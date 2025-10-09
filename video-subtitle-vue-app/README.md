# Video Subtitle Vue App

This project is a Vue.js application designed for managing video playback and displaying subtitles. It provides a clean and modern interface for users to edit and view subtitles over video content.

## Features

- **Video Playback**: Custom video player with controls for play, pause, volume, and seek.
- **Subtitle Management**: Load, parse, and display subtitles in various formats.
- **Responsive Design**: The application is designed to work on various screen sizes.
- **State Management**: Utilizes Vuex for managing application state.
- **Routing**: Vue Router is used for navigation between different pages.
- **Composables**: Custom composables for managing video and subtitle functionalities.

## Project Structure

```
video-subtitle-vue-app
├── src
│   ├── main.ts                # Entry point of the application
│   ├── App.vue                # Root component
│   ├── env.d.ts               # TypeScript declarations for environment variables
│   ├── assets                  # Contains static assets
│   │   └── styles             # Stylesheets
│   │       ├── base.css       # Base styles
│   │       └── variables.css   # CSS variables
│   ├── components              # Vue components
│   │   ├── video              # Video related components
│   │   │   ├── VideoPlayer.vue # Video player component
│   │   │   ├── VideoControls.vue # Video controls component
│   │   │   └── SubtitleOverlay.vue # Subtitle overlay component
│   │   └── ui                 # UI components
│   │       ├── Icon.vue       # Icon component
│   │       ├── AppButton.vue   # Button component
│   │       ├── AppSlider.vue    # Slider component
│   │       └── AppSelect.vue    # Select component
│   ├── modules                 # Modules for subtitles and video
│   │   ├── subtitles           # Subtitle management
│   │   │   ├── index.ts       # Exports for subtitles
│   │   │   ├── subtitleService.ts # Subtitle service
│   │   │   ├── subtitleParser.ts   # Subtitle parser
│   │   │   └── subtitleTypes.ts     # Subtitle types
│   │   └── video              # Video management
│   │       ├── index.ts       # Exports for video
│   │       ├── videoService.ts # Video service
│   │       └── videoTypes.ts   # Video types
│   ├── composables             # Composables for various functionalities
│   │   ├── useVideoPlayer.ts   # Video player composable
│   │   ├── useSubtitles.ts     # Subtitles composable
│   │   ├── useFullscreen.ts     # Fullscreen composable
│   │   ├── useKeyboardShortcuts.ts # Keyboard shortcuts composable
│   │   └── useResizeObserver.ts  # Resize observer composable
│   ├── store                   # Vuex store
│   │   ├── index.ts           # Store setup
│   │   ├── videoStore.ts      # Video store module
│   │   └── subtitleStore.ts   # Subtitle store module
│   ├── router                  # Vue Router setup
│   │   └── index.ts           # Router configuration
│   ├── utils                   # Utility functions
│   │   ├── time.ts            # Time utilities
│   │   ├── dom.ts             # DOM utilities
│   │   ├── formatting.ts       # Formatting utilities
│   │   └── math.ts            # Math utilities
│   ├── types                   # TypeScript types
│   │   └── globals.d.ts       # Global type declarations
│   ├── layouts                 # Layout components
│   │   └── DefaultLayout.vue   # Default layout
│   ├── pages                   # Page components
│   │   ├── EditorPage.vue      # Subtitle editing page
│   │   └── NotFoundPage.vue    # 404 page
│   └── config                  # Configuration files
│       └── subtitleDefaults.ts  # Default subtitle settings
├── public                      # Public assets
│   └── index.html             # Main HTML file
├── package.json                # Project metadata and dependencies
├── tsconfig.json              # TypeScript configuration
├── tsconfig.app.json          # App-specific TypeScript configuration
├── tsconfig.node.json         # Node-specific TypeScript configuration
├── vite.config.ts             # Vite configuration
├── postcss.config.cjs         # PostCSS configuration
├── tailwind.config.cjs        # Tailwind CSS configuration
├── .eslintrc.cjs              # ESLint configuration
├── .prettierrc                # Prettier configuration
└── README.md                  # Project documentation
```

## Getting Started

1. Clone the repository:
   ```
   git clone <repository-url>
   cd video-subtitle-vue-app
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Run the application:
   ```
   npm run dev
   ```

4. Open your browser and navigate to `http://localhost:3000`.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.