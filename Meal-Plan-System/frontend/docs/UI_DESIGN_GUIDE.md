# Glocusense UI Design Guide

Use this guide when adding or modifying UI components to keep the app balanced, properly sized, and well arranged.

## Design Tokens (index.css)

- **Spacing**: `--page-gap: 1.5rem`, `--card-padding: 1.5rem`, `--header-padding: 1.25rem 1.5rem`
- **Radius**: `--radius` (0.5rem), `--radius-lg` (0.75rem), `--radius-xl` (1rem)
- **Shadows**: `--shadow`, `--shadow-md`, `--shadow-lg`, `--shadow-xl`

## Page Structure

1. **Page header** – Use `page-header` for the main title block (gradient, white text):
   ```jsx
   <div className="page-header">
     <h1><i className="fas fa-icon" /> Page Title</h1>
     <p>Short description</p>
   </div>
   ```

2. **Page content** – Wrap all page content in `page-content` (provides consistent gap):
   ```jsx
   <div className="page-content">
     ...
   </div>
   ```

3. **Cards** – Use `card` for content blocks. Cards get consistent padding and radius. Use `card-header` for title + action rows.

## Icons (match landing page)

| Feature           | Icon              |
|-------------------|-------------------|
| Search / Food     | `fa-apple-whole`  |
| Nutrition / Chat  | `fa-comments`     |
| Glucose / Health | `fa-heart-pulse`  |
| Recommendations   | `fa-seedling`     |
| Logo              | `fa-leaf`         |

## Grids

- **grid-2** – Responsive 2-column grid for cards/items (min 280px, 300px on tablet+)
- Use `gap-2`, `gap-3`, `gap-4` for consistent spacing between flex/grid children

## Forms

- Use `form-label` for labels
- Use `form-group` (or `mb-3`) for vertical spacing between fields
- Use `form-row` for side-by-side fields (e.g. first/last name)

## Cards

- **card-clickable** – For links/buttons; adds min-height 140px, hover lift
- **card-header** – Flex row with title and action button
- List items: `p-4 bg-gray-50 rounded border-start` for reading/item blocks

## Alerts

- `alert alert-error` – Red background
- `alert alert-success` – Green background

## Responsive

- Cards reduce padding on mobile (1.25rem)
- grid-2 collapses to 1 column
- Use `hidden-mobile` to hide nav labels on small screens
