# UI Registry

This document catalogs the design system patterns, custom components, and visual rules for the project. AI agents must consult this registry to ensure consistency across the UI. Before creating a new component, check if an existing one can be reused.

## Design Tokens

### Colors
- **Primary**: `[hex code or css variable]` - [Usage description]
- **Secondary**: `[hex code or css variable]` - [Usage description]
- **Background**: `[hex code or css variable]` - [Usage description]
- **Text**: `[hex code or css variable]` - [Usage description]

### Typography
- **Headings**: `[Font Family, Weights]`
- **Body**: `[Font Family, Weights]`

### Spacing & Borders
- **Border Radius**: `[e.g., rounded-md for inputs, rounded-xl for cards]`

---

## Component Registry

### `[ComponentName]`
- **Description**: [What it is and when to use it]
- **Props**: `[Key props it accepts]`
- **Location**: `[Path to component file]`
- **Example Usage**:
  ```tsx
  <[ComponentName] prop="value" />
  ```

---

*(Note: Use the `/imprint` skill to extract and save new visual patterns here when building new UI components.)*
