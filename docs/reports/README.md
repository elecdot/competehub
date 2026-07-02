# Reports

This directory contains course reports, requirement-gathering materials, and generated analysis documents.

## Local Conventions

- Keep report documents separate from stable product and engineering docs.
- Prefer Markdown for editable source documents.
- Do not treat reports as the source of truth when they conflict with `docs/PRD.zh.md` or `docs/tech_spec.zh.md`.

## Documents

- `01_项目开发计划.md`: Project development plan formal report.
- `02_需求规格说明.md`: Requirements specification formal report.
- `03_软件设计说明.md`: Software design specification formal report.
- `requirements.md`: Requirement-gathering and initial requirement analysis report.
- `module_breakdown.md`: Course-assignment module split, interfaces, and member responsibilities.
- `module_breakdown_v1.0.md`: Revised module breakdown with responsibilities and detailed module descriptions (v1.0).

## Templates

- `templates/*.source.docx`: Original DOCX source files.
- `templates/*.template.md`: Converted Markdown templates kept for reference.

## Formal Reports

- Keep template files unchanged; create formal report files directly under
  `docs/reports/`.
- The first three formal reports are:
  - `01_项目开发计划.md`
  - `02_需求规格说明.md`
  - `03_软件设计说明.md`
- Use `大学生竞赛信息智能筛选与推荐系统` as the formal system name.
- Use `第七组` as the team number and `a, b, c, d, e, f` as member
  placeholders until real member names are provided.
- Use `2026-07-02` as the completion date unless the actual submission date
  changes.
- Use the following project-background placeholders until formal school names
  are provided: commissioning unit `软件工程课程设计课程组`, development unit
  `第七组`, and supervising unit `学院或课程教学管理单位`.
- In `01_项目开发计划.md`, separate immediate course-report delivery from the
  engineering roadmap. The 01/02/03 reports are current deliverables; the
  implementation phases should align with `docs/roadmap.md`.
- Prefer Markdown tables and Mermaid diagrams for maintainable report graphics.
  UML-style diagrams may be represented with Mermaid where useful. Do not add
  generated image assets before screenshots or exported diagrams are truly
  needed.
- Use the refined seven-module structure from `module_breakdown_v1.0.md` for
  formal reports. M1-M6 are the current core delivery scope, while M7 is an
  extension area. M5 owns recommendation calculation and explanation; M3 owns
  student-facing赛事 detail, fit-tag, and value-basis display.
- In `02_需求规格说明.md`, classify priorities as follows: high priority for
  M1-M6 functions that support the student main workflow and administrator
  publication workflow; medium priority for statistics, refined configuration,
  recommendation preference adjustment, negative feedback, and enhanced
  governance; low priority for M7, semi-automated collection candidates,
  external reminders, model-based recommendation, and dedicated teacher or
  organizer workspaces.
