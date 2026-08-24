# AI Platform Engineering Agent Workspace

This `.agents` directory serves as the "brain" for the project. All AI code generation and structural changes must follow the workflows and rules defined here.

## Structure
- `context/`: Contains the ground truth for our architecture, database schema, and UI registry. Agents must consult these before modifying code.
- `workflows/`: Defines the strict loops (Architect -> Review -> Imprint) for specific tasks.
- `skills/`: Contains custom scripts and tools for validation and code enforcement.
- `feature-specs/`: Stores the numbered, approved implementation plans (`01-feature.md`) for permanent documentation of what the AI has built.

---

<!-- BEGIN:nextjs-agent-rules -->
## Next.js Framework Rules
This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

## General Rules
1. **Documentation Sync**: Whenever you create a new core file, move a file, or change the architecture/database structure, you MUST immediately update `README.md` (specifically the 'Project Structure', 'Tech Stack', and 'Architecture' sections) to reflect reality. Never leave the README out of sync with the actual codebase.
<!-- END:nextjs-agent-rules -->
