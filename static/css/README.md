# BTZ Zeiterfassung CSS Architecture

This document describes the CSS architecture for the BTZ Zeiterfassung application.

## CSS Structure

Our CSS is organized in a modular way with the following components:

### Core Files

1. **variables.css**
   - Contains all global CSS variables (colors, spacing, typography, etc.)
   - Single source of truth for design tokens
   - Located at: `/static/css/variables.css`

2. **base.css**
   - Base styling for HTML elements
   - Core component styling (buttons, forms, tables, etc.)
   - Common utility classes
   - Located at: `/static/css/base.css`

3. **components.css**
   - Reusable UI components (badges, cards, modals, etc.)
   - Component-specific styling
   - Located at: `/static/css/components.css`

4. **main.css**
   - Application-specific layout and styling
   - Extends and customizes base and component styles
   - Located at: `/static/css/main.css`

### Feature-Specific Files

- **user-management.css** - Styles for user management page
- Other feature-specific CSS files follow the same pattern

## CSS Variables

We use CSS variables (custom properties) for consistent styling across the application:

- **Colors**: `--color-primary`, `--color-danger`, etc.
- **Spacing**: `--space-sm`, `--space-md`, etc.
- **Typography**: `--font-size-sm`, `--font-size-md`, etc.
- **Borders & Shadows**: `--border-radius-sm`, `--shadow-md`, etc.

Example:
```css
.button {
  background-color: var(--color-primary);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--border-radius-sm);
}
```

## Legacy CSS

The following files are part of the legacy CSS structure and are gradually being phased out:

- `/static/style.css`
- `/static/components.css` (replaced by `/static/css/components.css`)
- Various other utility CSS files

## Best Practices

1. **Always use CSS variables** for colors, spacing, and other design tokens
2. **Follow component-based styling** - create reusable components
3. **Avoid inline styles** - use class-based styling instead
4. **Maintain responsive design** - ensure styles work on all devices
5. **Document complex components** with comments
6. **Place new styles** in the appropriate files based on their scope

## Adding New Styles

When adding new styles:

1. For global design tokens: add to `variables.css`
2. For basic element styling: add to `base.css`
3. For reusable components: add to `components.css`
4. For page-specific styles: create or update feature-specific CSS
