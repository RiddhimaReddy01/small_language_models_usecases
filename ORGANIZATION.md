# Codebase Organization

This document explains the clean, reproducible structure of the SLM/LLM routing system.

## Directory Structure

```
SLM-LLM-Router/
│
├── src/                           # Core implementation
│   ├── __init__.py
│   ├── routing/                   # Routing system
│   │   ├── __init__.py
│   │   ├── production_router.py   # Main production router (Phase 0→1→2)
│   │   ├── framework.py           # Task-agnostic analysis framework
│   │   └── analysis.py            # Phase 0 analysis pipeline
│   └── utils/                     # Utilities
│       ├── __init__.py
│       └── thresholds.py          # Empirical threshold validation
│
├── docs/                          # Documentation (organized by purpose)
│   ├── guides/                    # How-to guides (user-facing)
│   │   ├── README.md              # Start here - quick overview
│   │   ├── IMPLEMENTATION.md      # Production deployment guide
│   │   ├── COMPLETE_PIPELINE.md   # 20-step detailed walkthrough
│   │   ├── ROUTING_POLICIES.md    # Zone policies with code
│   │   ├── EXECUTION_WALKTHROUGH.md  # Complete code examples
│   │   └── DECISION_TREE.md       # Visual decision flow
│   │
│   ├── architecture/              # System design (technical)
│   │   ├── SYSTEM_OVERVIEW.md     # 30-second system overview
│   │   └── DELIVERY_CHECKLIST.md  # What was delivered
│   │
│   └── reference/                 # Technical reference
│       ├── HYBRID_ROUTING.md      # Zone 3 hybrid routing
│       ├── QUALITY_METRICS.md     # Quality metric extraction
│       ├── RISK_CALCULATION.md    # Risk methodology
│       └── RISK_CURVES.md         # Reading capability/risk curves
│
├── tests/                         # Test suite
│   └── test_complete_pipeline_integration.py  # 20 integration tests
│
├── examples/                      # Working examples
│   └── example_code_generation.py # Complete end-to-end example
│
├── .archive/                      # Old/outdated files (not actively used)
│   ├── *.md                       # Deprecated documentation
│   ├── *.py                       # Deprecated scripts
│   └── README.md                  # Archive description
│
├── .gitignore                     # Git ignore rules
├── README.md                      # Project overview (this is main entry point)
├── ORGANIZATION.md                # This file - codebase structure
├── requirements.txt               # Python dependencies
├── setup.py                       # Package setup
└── .git/                          # Git history
```

## File Organization Principles

### src/ - Implementation Code

**Keep**: Only code that's actively used in production
- Core routing framework
- Production router
- Analysis utilities

**Archive**: Code from experiments, old versions, debugging scripts

### docs/ - Documentation

**Organize by usage pattern**, not chronologically:

1. **guides/** - "How do I...?" questions
   - For users getting started or deploying
   - Step-by-step instructions
   - Examples with real code

2. **architecture/** - System design and decisions
   - Why things work this way
   - What was delivered
   - Architectural tradeoffs

3. **reference/** - Technical deep-dives
   - For developers building on top
   - Detailed methodology
   - Algorithm explanations

### tests/ - Automated Tests

Keep only integration tests that validate the complete system:
- `test_complete_pipeline_integration.py` - 20 tests covering all phases

Other tests (sddf, benchmark, etc.) can be archived.

### examples/ - Working Code

Keep minimal, complete working examples:
- `example_code_generation.py` - Shows all three phases

Demonstrates real usage without cruft.

### .archive/ - Historical Content

Everything that was useful but isn't actively maintained:
- Deprecated analyses
- Old documentation
- Experimental code
- One-off scripts

Still in git history, just not cluttering the main workspace.

## What Counts as "Outdated"?

A file should be archived if:

1. **Superseded**: Newer version exists that does the same thing
   - Old framework versions → keep only latest
   - Old documentation → keep only current version

2. **Experimental**: Was used to explore an idea, not production code
   - Analysis scripts for "what if"
   - Debugging utilities
   - Validation checks that are now part of tests

3. **Infrastructure**: Used for setup/deployment but not core logic
   - Build scripts
   - Report generation
   - Data processing pipelines

4. **Historical**: Documents decisions or analyses but not current state
   - Old meeting notes
   - Outdated design docs
   - Historical analysis results

## How to Find Things

### "How do I get started?"
→ `README.md` → `docs/guides/README.md`

### "How do I deploy this?"
→ `docs/guides/IMPLEMENTATION.md`

### "How does the system work?"
→ `docs/architecture/SYSTEM_OVERVIEW.md` (30 seconds)
→ `docs/guides/COMPLETE_PIPELINE.md` (detailed)

### "Show me code"
→ `examples/example_code_generation.py`
→ `docs/guides/EXECUTION_WALKTHROUGH.md`

### "I want to understand zone Q3"
→ `docs/reference/HYBRID_ROUTING.md`

### "What quality metrics do I use?"
→ `docs/reference/QUALITY_METRICS.md`

### "What was delivered?"
→ `docs/architecture/DELIVERY_CHECKLIST.md`

## Development Workflow

### Adding New Code

1. Keep in `src/routing/` if it's part of core framework
2. Keep in `src/utils/` if it's a helper function
3. Add tests in `tests/test_*.py`
4. If experimental, use a feature branch

### Adding New Documentation

1. If it's a how-to: `docs/guides/`
2. If it's architecture/design: `docs/architecture/`
3. If it's technical reference: `docs/reference/`
4. If it's just notes: `.archive/` (or don't commit)

### Deprecating Something

1. Move to `.archive/` 
2. Add note in `.archive/README.md`
3. Commit with message "Archive: [reason]"

## Size Constraints

- **Total core code**: Keep under 2000 lines
- **Total documentation**: Keep under 50 pages of guides + reference
- **Examples**: Keep minimal, focused demonstrations

If adding significant new functionality, archive old experimental code first.

## Git History

All files, even archived ones, are in git history forever.

To see what used to be here:
```bash
git log --follow .archive/
git log -- 'docs/guides/IMPLEMENTATION.md'
```

Archiving keeps current workspace clean without losing history.

## Current Status

**Codebase State**: Clean and Organized ✓

- Core code: 6 Python files (750 lines total)
- Documentation: 12 markdown files (well-organized)
- Tests: 1 comprehensive test file (20 tests, all passing)
- Examples: 1 working example
- Outdated files: 40+ archived

Ready for production deployment.

---

Last updated: 2026-03-18
