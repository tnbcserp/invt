export default {
  theme: {
    extends: {
      colors: {
        // Primary brand colors for restaurant theme
        primary: "#2E666D", // Deep teal - professional restaurant color
        secondary: "#363A43", // Dark gray - sophisticated accent
        tertiary: "#F4A261", // Warm orange - food industry accent

        // Semantic colors
        success: "#00b894", // Green for good stock levels
        warning: "#fdcb6e", // Yellow for low stock warnings
        error: "#ff6b6b", // Red for critical alerts
        info: "#74b9ff", // Blue for information

        // Neutral colors
        white: "#ffffff",
        black: "#000000",
        gray: {
          50: "#f9fafb",
          100: "#f3f4f6",
          200: "#e5e7eb",
          300: "#d1d5db",
          400: "#9ca3af",
          500: "#6b7280",
          600: "#4b5563",
          700: "#374151",
          800: "#1f2937",
          900: "#111827"
        },

        // Restaurant-specific colors
        kitchen: {
          primary: "#2E666D",
          secondary: "#363A43",
          accent: "#F4A261",
          success: "#00b894",
          warning: "#fdcb6e",
          error: "#ff6b6b",
          info: "#74b9ff"
        }
      },

      // Typography scale optimized for restaurant management
      fontSizes: {
        xxs: "0.625rem", // 10px - fine print
        xs: "0.75rem",   // 12px - small labels
        sm: "0.875rem",  // 14px - body text
        md: "1rem",      // 16px - base size
        lg: "1.125rem",  // 18px - subheadings
        xl: "1.25rem",   // 20px - headings
        "2xl": "1.5rem", // 24px - section headers
        "3xl": "1.875rem", // 30px - page titles
        "4xl": "2.25rem",  // 36px - main titles
        "5xl": "3rem"      // 48px - hero text
      },

      // Font weights for hierarchy
      fontWeights: {
        light: 300,
        normal: 400,
        medium: 500,
        semibold: 600,
        bold: 700,
        extrabold: 800
      },

      // Line heights for readability
      lineHeights: {
        tight: 1.25,
        normal: 1.5,
        relaxed: 1.75
      },

      // Spacing scale for consistent layout
      spacing: {
        0: "0",
        1: "0.25rem",  // 4px
        2: "0.5rem",   // 8px
        3: "0.75rem",  // 12px
        4: "1rem",     // 16px
        5: "1.25rem",  // 20px
        6: "1.5rem",   // 24px
        8: "2rem",     // 32px
        10: "2.5rem",  // 40px
        12: "3rem",    // 48px
        16: "4rem",    // 64px
        20: "5rem",    // 80px
        24: "6rem"     // 96px
      },

      // Border radius for modern UI
      radius: {
        none: "0",
        sm: "0.125rem",   // 2px
        md: "0.375rem",   // 6px
        lg: "0.5rem",     // 8px
        xl: "0.75rem",    // 12px
        "2xl": "1rem",    // 16px
        "3xl": "1.5rem",  // 24px
        full: "9999px"    // pill
      },

      // Border widths
      borderWidths: {
        0: "0",
        1: "1px",
        2: "2px",
        4: "4px",
        8: "8px"
      },

      // Shadows for depth
      shadows: {
        sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        xl: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        "2xl": "0 25px 50px -12px rgba(0, 0, 0, 0.25)"
      },

      // Component-specific tokens
      components: {
        button: {
          primary: {
            backgroundColor: "$primary",
            color: "$white",
            borderRadius: "$lg",
            padding: "$3 $6",
            fontSize: "$md",
            fontWeight: "$medium",
            border: "none",
            cursor: "pointer",
            transition: "all 0.2s ease",
            "&:hover": {
              backgroundColor: "$secondary",
              transform: "translateY(-1px)",
              boxShadow: "$md"
            },
            "&:active": {
              transform: "translateY(0)"
            }
          },
          secondary: {
            backgroundColor: "transparent",
            color: "$primary",
            border: "2px solid $primary",
            borderRadius: "$lg",
            padding: "$3 $6",
            fontSize: "$md",
            fontWeight: "$medium",
            cursor: "pointer",
            transition: "all 0.2s ease",
            "&:hover": {
              backgroundColor: "$primary",
              color: "$white"
            }
          }
        },
        card: {
          default: {
            backgroundColor: "$white",
            borderRadius: "$xl",
            padding: "$6",
            boxShadow: "$md",
            border: "1px solid $gray200",
            transition: "all 0.2s ease",
            "&:hover": {
              boxShadow: "$lg",
              transform: "translateY(-2px)"
            }
          },
          metric: {
            background: "linear-gradient(135deg, $primary 0%, $secondary 100%)",
            color: "$white",
            borderRadius: "$xl",
            padding: "$6",
            boxShadow: "$lg",
            textAlign: "center"
          },
          alert: {
            backgroundColor: "$error",
            color: "$white",
            borderRadius: "$lg",
            padding: "$4",
            boxShadow: "$md",
            borderLeft: "4px solid $error"
          }
        },
        navigation: {
          background: "linear-gradient(135deg, $primary 0%, $secondary 100%)",
          color: "$white",
          padding: "$4",
          boxShadow: "$md"
        }
      }
    }
  }
};

