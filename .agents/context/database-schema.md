# Database Schema

This document represents the current ground truth of the database schema for the project. Agents should refer to this file to understand available tables, columns, relations, and data types before writing any database queries or mutations.

## Tables

### `[table_name]`
- Description: [Brief description of the table's purpose]
- Relations:
  - [e.g. Belongs to User]
  - [e.g. Has many Posts]

#### Columns
| Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key | Unique identifier |
| `created_at` | Timestamp | Not Null | Creation timestamp |
| `[column_name]` | `[Type]` | `[Constraints]` | `[Description]` |

---

*(Note: When initializing a new project, AI agents will populate this schema based on the approved architecture.)*
