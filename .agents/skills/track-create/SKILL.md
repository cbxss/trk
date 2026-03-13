---
name: track-create
description: Set up domain-specific tracking for any workflow. Asks questions, generates tracking.md with domain vocabulary, starts tracking session. Use when asked to "start tracking", "track this project", "set up tracking for X".
---

# Track-Create Skill

Set up domain-specific tracking. Works like autoresearch-create but for generic work tracking.

## Setup Workflow

1. **Ask or infer from context:**
   - **Domain** — What type of work? (`security-research`, `data-migration`, `debugging`, `refactoring`)
   - **Target** — What's being tracked? (`doordash`, `production_db`, `heap-bug`)
   - **Work item term** — What do you call tasks? (hypothesis, migration, bug-theory, task)
   - **Confirmation term** — What's a success? (vulnerability, applied-migration, root-cause, completed)
   - **Status progression** — How do confirmations evolve? (e.g. `confirmed → needs_exfil → submitted → paid`)
   - **Files in scope** — What can be modified?
   - **Off limits** — What must NOT be touched?

2. **Create branch:** `git checkout -b track/<target>-<date>`

3. **Write `tracking.md`** (the domain configuration document):

```markdown
# Tracking: <target>

## Domain
<domain-name>

## Target
<target-name>

## Vocabulary
- **Work Item** = <work-item-term> (<what it represents>)
- **Confirmation** = <confirmation-term> (<what it represents>)  
- **Attempt** = <attempt-term> (<what each try represents>)

## Status Progression
<status flow for confirmations>

Example: confirmed → confirmed_needs_exfil → confirmed_needs_poc → submitted → bounty_paid

## Commands (domain meaning)

When I say:
- "Create <work-item-term>" → you run `track new --desc "..."`
- "Record <attempt-term>" → you run `track try <ID> "..." --result "..."`
- "Close <work-item-term>" → you run `track close <ID> --conclusion "..."`
- "Confirm <confirmation-term>" → you run `track confirm <ID> --title "..." --severity <level>`

## Files in Scope
<List files/directories that can be modified>

## Off Limits
<What must NOT be touched>

## Rules
1. Always start sessions with `track show`
2. Use `track grep` before trying anything new (avoid duplicate work)
3. Record every <attempt-term> with `track try` before moving on
4. Use queues (`track qadd`) to enumerate all items before drilling into any
5. Close dead ends immediately with `track close`
6. Confirm successes with `track confirm`
7. Update `track last` after significant steps

## What's Been Tried
<Update this section as work progresses>

### Key Wins
(Record successful approaches here)

### Dead Ends  
(Record what didn't work and why)

### Patterns Discovered
(Record insights about the domain)
```

4. **Commit tracking.md**

5. **Initialize tracking:**
   ```bash
   track init <target>
   track show
   ```

6. **Start working** using domain vocabulary from tracking.md

## Example: Security Research

```
User: "start tracking this bug bounty"

Agent asks (or infers):
- Domain? security-research
- Target? doordash  
- Work item term? hypothesis
- Confirmation term? vulnerability
- Status progression? confirmed → needs_exfil → needs_poc → submitted → bounty_paid

Agent writes tracking.md with these terms
Agent: track init doordash
Agent: "What should I investigate first?"

User: "check postMessage handlers"
Agent: "Creating hypothesis H1 for XSS via postMessage"
       track new --desc "XSS via postMessage" --priority 1
       track qadd --queue listeners --desc "chunk_abc.js L123 navigate handler"
       ...
```

## Example: Data Migration

```
User: "track this migration"

Agent asks:
- Domain? data-migration
- Target? production_users_db
- Work item term? migration
- Confirmation term? applied-migration
- Status progression? planned → testing → validated → applied → rolled_back

Agent writes tracking.md
Agent: track init production_users_db
Agent: "What migrations do we need?"

User: "add user_preferences table"
Agent: "Creating migration M1"
       track new --desc "Add user_preferences table"
       track try M1 "CREATE TABLE..." --result "FK constraint error"
       ...
```

## Key Points

- **tracking.md is the session document** — like autoresearch.md
- **Agent reads it at session start** to understand domain vocabulary
- **No separate skill file needed** — tracking.md IS the domain knowledge
- **Update "What's Been Tried"** as work progresses
- **Resuming:** read tracking.md + `track show` to continue where you left off

## Notes

- tracking.md lives in project root (committed to git)
- Agent uses terminology from tracking.md naturally
- Each project has its own tracking.md with custom vocabulary
- The `track` CLI is 100% generic and domain-agnostic
