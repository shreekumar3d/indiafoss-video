/*
 * fullscreen_color.c
 * Human checked, but Claude coded to begin with:
 *
 * I have a laptop. Create a SDL fullscreen app, which runs without borders on
 * the external display, which will be connected to HDMI. app will fill
 * repainting the screen with a single color, waiting for vertical refresh
 * for every frame.
 *
 * Build: gcc -o fullscreen_color fullscreen_color.c -lSDL2
 */
#include <SDL2/SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

// Color definitions (RGB values)
typedef struct {
    Uint8 r, g, b;
    const char* name;
} Color;

static Color colors[] = {
    {255, 0, 0, "Red"},
    {0, 255, 0, "Green"},
    {0, 0, 255, "Blue"},
    {255, 255, 255, "White"},
    {0, 0, 0, "Black"},
    {255, 255, 0, "Yellow"},
    {255, 0, 255, "Magenta"},
    {0, 255, 255, "Cyan"},
    {128, 128, 128, "Gray"},
    {255, 165, 0, "Orange"}
};

static const int num_colors = sizeof(colors) / sizeof(colors[0]);

int find_external_display() {
    int num_displays = SDL_GetNumVideoDisplays();

    printf("Found %d display(s):\n", num_displays);

    for (int i = 0; i < num_displays; i++) {
        SDL_DisplayMode mode;
        const char* display_name = SDL_GetDisplayName(i);

        if (SDL_GetCurrentDisplayMode(i, &mode) == 0) {
            printf("  Display %d: %s - %dx%d @ %dHz\n",
                   i, display_name ? display_name : "Unknown",
                   mode.w, mode.h, mode.refresh_rate);
        }
    }

    // If we have multiple displays, assume display 1 is external
    // You can modify this logic based on your setup
    if (num_displays > 1) {
        printf("Using display 1 (assumed external)\n");
        return 1;
    } else {
        printf("Using display 0 (only display available)\n");
        return 0;
    }
}

int main(int argc, char* argv[]) {
    SDL_Window* window = NULL;
    SDL_Renderer* renderer = NULL;
    SDL_Event event;
    bool running = true;
    int current_color = 0;
    int target_display = 0;

    // Initialize SDL
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        fprintf(stderr, "SDL initialization failed: %s\n", SDL_GetError());
        return 1;
    }

    printf("SDL initialized successfully\n");

    // Find external display
    target_display = find_external_display();

    // Get display bounds for the target display
    SDL_Rect display_bounds;
    if (SDL_GetDisplayBounds(target_display, &display_bounds) != 0) {
        fprintf(stderr, "Failed to get display bounds: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    printf("Target display bounds: %dx%d at (%d, %d)\n",
           display_bounds.w, display_bounds.h, display_bounds.x, display_bounds.y);

    // Create fullscreen window on the target display
    window = SDL_CreateWindow("Fullscreen Color Display",
                              display_bounds.x, display_bounds.y,
                              display_bounds.w, display_bounds.h,
                              SDL_WINDOW_FULLSCREEN_DESKTOP | SDL_WINDOW_BORDERLESS);

    if (!window) {
        fprintf(stderr, "Window creation failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    printf("Window created successfully\n");

    // Create renderer with vsync enabled
    renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);

    if (!renderer) {
        fprintf(stderr, "Renderer creation failed: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }

    printf("Renderer created with VSync enabled\n");

    // Check if vsync is actually enabled
    SDL_RendererInfo renderer_info;
    SDL_GetRendererInfo(renderer, &renderer_info);
    if (renderer_info.flags & SDL_RENDERER_PRESENTVSYNC) {
        printf("VSync is active\n");
    } else {
        printf("Warning: VSync may not be active\n");
    }

    printf("\nControls:\n");
    printf("  SPACE: Change color\n");
    printf("  ESC or Q: Quit\n");
    printf("  F: Toggle fullscreen\n");
    printf("\nStarting with color: %s\n", colors[current_color].name);

    // Hide cursor
    SDL_ShowCursor(SDL_DISABLE);

    // Main loop
    while (running) {
        // Handle events
        while (SDL_PollEvent(&event)) {
            switch (event.type) {
                case SDL_QUIT:
                    running = false;
                    break;

                case SDL_KEYDOWN:
                    switch (event.key.keysym.sym) {
                        case SDLK_ESCAPE:
                        case SDLK_q:
                            running = false;
                            break;

                        case SDLK_SPACE:
                            current_color = (current_color + 1) % num_colors;
                            printf("Changed to color: %s\n", colors[current_color].name);
                            break;

                        case SDLK_f:
                            {
                                Uint32 flags = SDL_GetWindowFlags(window);
                                if (flags & SDL_WINDOW_FULLSCREEN_DESKTOP) {
                                    SDL_SetWindowFullscreen(window, 0);
                                    printf("Exited fullscreen\n");
                                } else {
                                    SDL_SetWindowFullscreen(window, SDL_WINDOW_FULLSCREEN_DESKTOP);
                                    printf("Entered fullscreen\n");
                                }
                            }
                            break;
                    }
                    break;

                case SDL_WINDOWEVENT:
                    if (event.window.event == SDL_WINDOWEVENT_CLOSE) {
                        running = false;
                    }
                    break;
            }
        }

        // Clear screen with current color
        SDL_SetRenderDrawColor(renderer,
                              colors[current_color].r,
                              colors[current_color].g,
                              colors[current_color].b,
                              255);

        // Clear the entire screen
        SDL_RenderClear(renderer);

        // Present the frame (waits for vsync)
        SDL_RenderPresent(renderer);
    }

    printf("\nShutting down...\n");

    // Show cursor again
    SDL_ShowCursor(SDL_ENABLE);

    // Cleanup
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();

    return 0;
}
