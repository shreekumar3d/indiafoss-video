/*
 * camera_stream.c
 * Human checked, but Claude generated code, mostly
 *
 * gcc -o camera_stream camera_stream.c
 *
 * Prompt:
 * need a C program to initialize a camera using v4l, set image format to YUV2,
 * 1080p at 60 hz, and stream images in a loop using memory mapping. For every
 * frame, check if all the pixels are the same.  If any pixel fails this test,
 * dump the components of the failing pixel
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/videodev2.h>
#include <stdint.h>

#define CLEAR(x) memset(&(x), 0, sizeof(x))
#define DEVICE_NAME "/dev/video0"
#define NUM_BUFFERS 4

struct buffer {
    void *start;
    size_t length;
};

struct camera {
    int fd;
    struct buffer *buffers;
    unsigned int n_buffers;
    int width;
    int height;
};

// YUV422 pixel structure (YUYV format)
typedef struct {
    uint8_t y;
    uint8_t u;
    uint8_t v;
} yuv_pixel_t;

static void errno_exit(const char *s) {
    fprintf(stderr, "%s error %d, %s\n", s, errno, strerror(errno));
    exit(EXIT_FAILURE);
}

static int xioctl(int fh, int request, void *arg) {
    int r;
    do {
        r = ioctl(fh, request, arg);
    } while (-1 == r && EINTR == errno);
    return r;
}

// Extract YUV components from YUYV buffer at given pixel position
static yuv_pixel_t get_yuv_pixel(uint8_t *buffer, int x, int y, int width) {
    yuv_pixel_t pixel;
    int pixel_index = y * width + x;
    int byte_index = pixel_index * 2; // 2 bytes per pixel in YUYV

    // YUYV format: Y0 U0 Y1 V0 (4 bytes for 2 pixels)
    if (x % 2 == 0) {
        // Even pixel
        pixel.y = buffer[byte_index];
        pixel.u = buffer[byte_index + 1];
        pixel.v = buffer[byte_index + 3];
    } else {
        // Odd pixel
        pixel.y = buffer[byte_index];
        pixel.u = buffer[byte_index - 1];
        pixel.v = buffer[byte_index + 1];
    }

    return pixel;
}

static int check_pixel_uniformity(uint8_t *buffer, int width, int height) {
    if (width <= 0 || height <= 0) {
        return 0;
    }

    // Get reference pixel (first pixel)
    yuv_pixel_t ref_pixel = get_yuv_pixel(buffer, 0, 0, width);

    printf("Reference pixel: Y=%d, U=%d, V=%d\n", ref_pixel.y, ref_pixel.u, ref_pixel.v);

    // Check all pixels against reference
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            yuv_pixel_t current_pixel = get_yuv_pixel(buffer, x, y, width);

            if (current_pixel.y != ref_pixel.y ||
                current_pixel.u != ref_pixel.u ||
                current_pixel.v != ref_pixel.v) {

                printf("PIXEL MISMATCH at (%d, %d): Y=%d, U=%d, V=%d (expected Y=%d, U=%d, V=%d)\n",
                       x, y, current_pixel.y, current_pixel.u, current_pixel.v,
                       ref_pixel.y, ref_pixel.u, ref_pixel.v);
                return 0; // Non-uniform
            }
        }
    }

    printf("All pixels are uniform!\n");
    return 1; // Uniform
}

static void init_device(struct camera *cam) {
    struct v4l2_capability cap;
    struct v4l2_cropcap cropcap;
    struct v4l2_crop crop;
    struct v4l2_format fmt;
    struct v4l2_streamparm streamparm;
    unsigned int min;

    if (-1 == xioctl(cam->fd, VIDIOC_QUERYCAP, &cap)) {
        if (EINVAL == errno) {
            fprintf(stderr, "%s is no V4L2 device\n", DEVICE_NAME);
            exit(EXIT_FAILURE);
        } else {
            errno_exit("VIDIOC_QUERYCAP");
        }
    }

    if (!(cap.capabilities & V4L2_CAP_VIDEO_CAPTURE)) {
        fprintf(stderr, "%s is no video capture device\n", DEVICE_NAME);
        exit(EXIT_FAILURE);
    }

    if (!(cap.capabilities & V4L2_CAP_STREAMING)) {
        fprintf(stderr, "%s does not support streaming i/o\n", DEVICE_NAME);
        exit(EXIT_FAILURE);
    }

    // Select video input, video standard and tune here
    CLEAR(cropcap);
    cropcap.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;

    if (0 == xioctl(cam->fd, VIDIOC_CROPCAP, &cropcap)) {
        crop.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        crop.c = cropcap.defrect; // reset to default

        if (-1 == xioctl(cam->fd, VIDIOC_S_CROP, &crop)) {
            switch (errno) {
            case EINVAL:
                // Cropping not supported
                break;
            default:
                // Errors ignored
                break;
            }
        }
    } else {
        // Errors ignored
    }

    // Set format
    CLEAR(fmt);
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width = 1920;
    fmt.fmt.pix.height = 1080;
    fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_YUYV; // YUV422
    fmt.fmt.pix.field = V4L2_FIELD_INTERLACED;

    if (-1 == xioctl(cam->fd, VIDIOC_S_FMT, &fmt))
        errno_exit("VIDIOC_S_FMT");

    // Verify format was set correctly
    if (fmt.fmt.pix.pixelformat != V4L2_PIX_FMT_YUYV) {
        printf("Warning: Camera doesn't support YUYV, using format: %c%c%c%c\n",
               fmt.fmt.pix.pixelformat & 0xFF,
               (fmt.fmt.pix.pixelformat >> 8) & 0xFF,
               (fmt.fmt.pix.pixelformat >> 16) & 0xFF,
               (fmt.fmt.pix.pixelformat >> 24) & 0xFF);
    }

    cam->width = fmt.fmt.pix.width;
    cam->height = fmt.fmt.pix.height;

    printf("Format set to: %dx%d, pixelformat: %c%c%c%c\n",
           cam->width, cam->height,
           fmt.fmt.pix.pixelformat & 0xFF,
           (fmt.fmt.pix.pixelformat >> 8) & 0xFF,
           (fmt.fmt.pix.pixelformat >> 16) & 0xFF,
           (fmt.fmt.pix.pixelformat >> 24) & 0xFF);

    // Set frame rate to 60 fps
    CLEAR(streamparm);
    streamparm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;

    if (-1 == xioctl(cam->fd, VIDIOC_G_PARM, &streamparm)) {
        printf("Warning: Unable to get stream parameters\n");
    } else {
        if (streamparm.parm.capture.capability & V4L2_CAP_TIMEPERFRAME) {
            streamparm.parm.capture.timeperframe.numerator = 1;
            streamparm.parm.capture.timeperframe.denominator = 60;

            if (-1 == xioctl(cam->fd, VIDIOC_S_PARM, &streamparm)) {
                printf("Warning: Unable to set 60 fps\n");
            } else {
                printf("Frame rate set to: %d/%d fps\n",
                       streamparm.parm.capture.timeperframe.denominator,
                       streamparm.parm.capture.timeperframe.numerator);
            }
        }
    }

    // Buggy driver paranoia
    min = fmt.fmt.pix.width * 2;
    if (fmt.fmt.pix.bytesperline < min)
        fmt.fmt.pix.bytesperline = min;
    min = fmt.fmt.pix.bytesperline * fmt.fmt.pix.height;
    if (fmt.fmt.pix.sizeimage < min)
        fmt.fmt.pix.sizeimage = min;
}

static void init_mmap(struct camera *cam) {
    struct v4l2_requestbuffers req;

    CLEAR(req);
    req.count = NUM_BUFFERS;
    req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    req.memory = V4L2_MEMORY_MMAP;

    if (-1 == xioctl(cam->fd, VIDIOC_REQBUFS, &req)) {
        if (EINVAL == errno) {
            fprintf(stderr, "%s does not support memory mapping\n", DEVICE_NAME);
            exit(EXIT_FAILURE);
        } else {
            errno_exit("VIDIOC_REQBUFS");
        }
    }

    if (req.count < 2) {
        fprintf(stderr, "Insufficient buffer memory on %s\n", DEVICE_NAME);
        exit(EXIT_FAILURE);
    }

    cam->buffers = calloc(req.count, sizeof(*(cam->buffers)));

    if (!cam->buffers) {
        fprintf(stderr, "Out of memory\n");
        exit(EXIT_FAILURE);
    }

    for (cam->n_buffers = 0; cam->n_buffers < req.count; ++cam->n_buffers) {
        struct v4l2_buffer buf;

        CLEAR(buf);
        buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_MMAP;
        buf.index = cam->n_buffers;

        if (-1 == xioctl(cam->fd, VIDIOC_QUERYBUF, &buf))
            errno_exit("VIDIOC_QUERYBUF");

        cam->buffers[cam->n_buffers].length = buf.length;
        cam->buffers[cam->n_buffers].start =
            mmap(NULL, buf.length, PROT_READ | PROT_WRITE, MAP_SHARED,
                 cam->fd, buf.m.offset);

        if (MAP_FAILED == cam->buffers[cam->n_buffers].start)
            errno_exit("mmap");
    }

    printf("Initialized %d memory mapped buffers\n", cam->n_buffers);
}

static void start_capturing(struct camera *cam) {
    unsigned int i;
    enum v4l2_buf_type type;

    for (i = 0; i < cam->n_buffers; ++i) {
        struct v4l2_buffer buf;

        CLEAR(buf);
        buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_MMAP;
        buf.index = i;

        if (-1 == xioctl(cam->fd, VIDIOC_QBUF, &buf))
            errno_exit("VIDIOC_QBUF");
    }

    type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (-1 == xioctl(cam->fd, VIDIOC_STREAMON, &type))
        errno_exit("VIDIOC_STREAMON");

    printf("Started streaming\n");
}

static void stop_capturing(struct camera *cam) {
    enum v4l2_buf_type type;

    type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (-1 == xioctl(cam->fd, VIDIOC_STREAMOFF, &type))
        errno_exit("VIDIOC_STREAMOFF");

    printf("Stopped streaming\n");
}

static int read_frame(struct camera *cam) {
    struct v4l2_buffer buf;
    unsigned int i;

    CLEAR(buf);
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;

    if (-1 == xioctl(cam->fd, VIDIOC_DQBUF, &buf)) {
        switch (errno) {
        case EAGAIN:
            return 0;
        case EIO:
            // Could ignore EIO, see spec
        default:
            errno_exit("VIDIOC_DQBUF");
        }
    }

    assert(buf.index < cam->n_buffers);

    // Process the frame - check pixel uniformity
    printf("Frame %d captured, size: %d bytes\n", buf.sequence, buf.bytesused);
    check_pixel_uniformity((uint8_t *)cam->buffers[buf.index].start,
                          cam->width, cam->height);

    if (-1 == xioctl(cam->fd, VIDIOC_QBUF, &buf))
        errno_exit("VIDIOC_QBUF");

    return 1;
}

static void cleanup(struct camera *cam) {
    unsigned int i;

    if (cam->buffers) {
        for (i = 0; i < cam->n_buffers; ++i) {
            if (-1 == munmap(cam->buffers[i].start, cam->buffers[i].length))
                errno_exit("munmap");
        }
        free(cam->buffers);
    }

    if (cam->fd != -1) {
        close(cam->fd);
    }
}

int main(void) {
    struct camera cam = {0};
    fd_set fds;
    struct timeval tv;
    int r;
    int frame_count = 0;
    int max_frames = 100; // Limit for demo purposes

    // Open device
    cam.fd = open(DEVICE_NAME, O_RDWR | O_NONBLOCK, 0);
    if (-1 == cam.fd) {
        fprintf(stderr, "Cannot open '%s': %d, %s\n",
                DEVICE_NAME, errno, strerror(errno));
        exit(EXIT_FAILURE);
    }

    printf("Opened camera device: %s\n", DEVICE_NAME);

    // Initialize device
    init_device(&cam);
    init_mmap(&cam);
    start_capturing(&cam);

    printf("Starting capture loop (will capture %d frames)...\n", max_frames);

    // Main capture loop
    while (frame_count < max_frames) {
        FD_ZERO(&fds);
        FD_SET(cam.fd, &fds);

        // Timeout
        tv.tv_sec = 2;
        tv.tv_usec = 0;

        r = select(cam.fd + 1, &fds, NULL, NULL, &tv);

        if (-1 == r) {
            if (EINTR == errno)
                continue;
            errno_exit("select");
        }

        if (0 == r) {
            fprintf(stderr, "select timeout\n");
            exit(EXIT_FAILURE);
        }

        if (read_frame(&cam)) {
            frame_count++;
            printf("Processed frame %d/%d\n\n", frame_count, max_frames);
        }
    }

    stop_capturing(&cam);
    cleanup(&cam);

    printf("Capture complete. Processed %d frames.\n", frame_count);
    return 0;
}
