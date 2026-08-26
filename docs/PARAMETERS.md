# Parameters Reference

Complete parameter documentation for each tool in the GitHub Project Management MCP server.

---

## discover_ids

Discovers project ID, field IDs, and option IDs from the GitHub Project V2 API.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `force` | `bool` | Optional | `false` | Bypass the 24-hour cache and force a fresh API discovery query |

---

## list_project_items

Lists project board items with optional field-based filtering. Returns up to 200 items.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | `string` | Optional | `null` | Filter by Status column value (exact match against project board status) |
| `priority` | `string` | Optional | `null` | Filter by Priority field value (exact match against project priority) |
| `labels` | `list[string]` | Optional | `null` | Filter by label names; items matching any label in the list are included |
| `assignee` | `string` | Optional | `null` | Filter by assignee GitHub username (exact match, case-insensitive) |
| `milestone` | `string` | Optional | `null` | Filter by milestone title (exact match against milestone name) |
| `due_date` | `string` | Optional | `null` | ISO 8601 date string in YYYY-MM-DD format for date comparison filtering |
| `due_date_op` | `string` | Optional | `null` | Comparison operator for due_date: "before", "after", or "exact" |

### Valid Status Values

| Value | Description |
|-------|-------------|
| `Backlog` | Items not yet scheduled for active development work |
| `Todo` | Items scheduled and ready to be picked up for work |
| `In Progress` | Items currently being actively worked on by assignees |
| `In Review` | Items completed and awaiting code review or approval |
| `Done` | Items that have been completed and verified successfully |
| `Trash` | Items discarded or no longer relevant to the project |

### Valid Priority Values

| Value | Description |
|-------|-------------|
| `Urgent` | Critical items requiring immediate attention and resolution |
| `High` | Important items that should be addressed in the current sprint |
| `Medium` | Standard priority items for normal development scheduling |
| `Low` | Items that can be deferred to future development cycles |

### Due Date Operators

| Operator | Description |
|----------|-------------|
| `before` | Returns items with due date strictly before the specified date |
| `after` | Returns items with due date strictly after the specified date |
| `exact` | Returns items with due date exactly matching the specified date |

---

## create_project_item

Creates a new GitHub issue in the repository and adds it to the project board with optional field values.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | `string` | Required | — | Issue title between 1 and 256 characters inclusive |
| `body` | `string` | Optional | `""` | Issue body content, supports Markdown, maximum 65536 characters |
| `status` | `string` | Optional | `null` | Status field value to set on the project item after creation |
| `priority` | `string` | Optional | `null` | Priority field value to set on the project item after creation |
| `milestone` | `string` | Optional | `null` | Milestone title to assign to the issue (must exist in repository) |
| `due_date` | `string` | Optional | `null` | Due date in ISO 8601 format (YYYY-MM-DD) to set on the project item |
| `assignees` | `list[string]` | Optional | `null` | List of GitHub usernames to assign to the created issue |
| `labels` | `list[string]` | Optional | `null` | List of label names to apply to the created issue |

### Title Constraints

| Constraint | Value | Description |
|------------|-------|-------------|
| Minimum length | 1 character | Title cannot be empty; at least one character required |
| Maximum length | 256 characters | Exceeding this limit returns a validation error response |

### Body Constraints

| Constraint | Value | Description |
|------------|-------|-------------|
| Minimum length | 0 characters | Body is optional and can be left empty |
| Maximum length | 65536 characters | Maximum content length for issue body text |

---

## update_project_item_fields

Updates one or more fields on an existing project item. Each field is updated independently and reported individually.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `item_id` | `string` | Required | — | Project item node ID (e.g., "PVTI_...") identifying the item to update |
| `fields` | `dict[string, any]` | Required | — | Dictionary of field name to value pairs for the fields to update |

### Supported Field Names and Value Types

| Field Name | Value Type | Description |
|------------|-----------|-------------|
| `Status` | `string` | Single-select status value (must match a valid project status option) |
| `Priority` | `string` | Single-select priority value (must match a valid project priority option) |
| `Milestone` | `string` | Milestone title string (must exist as a milestone in the repository) |
| `Due date` | `string` | ISO 8601 date string in YYYY-MM-DD format for the item due date |
| `body` | `string` | Issue body content as a Markdown string (updates via Issues API) |
| `assignees` | `list[string]` | List of GitHub usernames; replaces all current assignees completely |
| `labels` | `list[string]` | List of label names; replaces all current labels on the issue |

### Update Behavior

- Each field is updated independently; failure of one does not block others
- Response reports per-field outcomes (success with value, or failure with reason)
- Assignee updates replace the entire list — provide all desired assignees each time
- Label updates replace the entire list — provide all desired labels each time

---

## set_estimate

Sets the time estimate (in hours) on a project item. Creates the Estimate field if it does not exist.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `item_id` | `string` | Required | — | Project item node ID identifying the item to set the estimate on |
| `value` | `float` | Required | — | Estimate in hours; must be between 0.25 and 9999 in 0.25 increments |

### Estimate Constraints

| Constraint | Value | Description |
|------------|-------|-------------|
| Minimum | 0.25 | Smallest allowable estimate representing 15 minutes of work |
| Maximum | 9999 | Largest allowable estimate in hours for a single item |
| Granularity | 0.25 | Values must be multiples of 0.25 (quarter-hour increments) |

### Valid Estimate Examples

| Value | Meaning |
|-------|---------|
| `0.25` | Fifteen minutes of estimated work effort |
| `1.0` | One hour of estimated work effort |
| `4.5` | Four and a half hours of estimated work effort |
| `8.0` | One full working day of estimated effort |
| `40.0` | One full working week of estimated effort |

---

## archive_project_item

Archives an item from the project board. The underlying issue remains open and unmodified.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `item_id` | `string` | Required | — | Project item node ID identifying the item to archive from the board |

### Behavior Notes

- Archiving is idempotent: archiving an already-archived item returns success
- The underlying GitHub issue is not affected (remains open unless separately closed)
- Archived items can be restored from the project board UI but not via this tool

---

## move_to_done

Moves an item's Status field to "Done". This is a convenience wrapper around update_project_item_fields.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `item_id` | `string` | Required | — | Project item node ID identifying the item to move to Done status |

### Behavior Notes

- Idempotent: moving an item already in Done status returns success with no-change message
- Does not close the underlying issue; use `close_issue` separately if needed

---

## move_to_trash

Moves an item's Status field to "Trash". This is a convenience wrapper around update_project_item_fields.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `item_id` | `string` | Required | — | Project item node ID identifying the item to move to Trash status |

### Behavior Notes

- Idempotent: moving an item already in Trash status returns success with no-change message
- Does not archive or delete the item; it remains visible on the board in the Trash column

---

## close_issue

Closes the underlying GitHub issue by issue number. Does not modify the project board item.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `issue_number` | `int` | Required | — | GitHub issue number (positive integer) within the configured target repository |

### Behavior Notes

- Cannot close DraftIssues — returns a validation error with suggestion to archive instead
- Closing an already-closed issue is idempotent and returns success
- The project board item is not archived automatically; use `archive_project_item` if needed

---

## Global Configuration

These values apply across all tools and are configured at the server level.

| Setting | Value | Description |
|---------|-------|-------------|
| Organization | (configured) | GitHub owner (org or user) from GH_PROJECT_ORG_NAME |
| Repository | (configured) | Repository from GH_PROJECT_REPO_NAME |
| Project number | (configured) | GitHub Project V2 number from GH_PROJECT_PROJECT_NUMBER |
| Timeout | `10s` (1–120s) | Maximum time for a single API request before timeout error |
| Retry attempts | `1` (0–5) | Read timeouts only; mutations are never retried |
| Retry delay | `2.0s` (0–60s) | Initial delay before exponential read retry |
| Cache TTL | `24h` (1–720h) | Duration for which discovered metadata remains valid locally |
| Cache path | `.github_project_cache.json` | Configurable private metadata cache path |
| Page size | `100` (1–100) | Maximum GraphQL page size used by list operations |
| Max items | `200` (1–1,000) | Maximum number of items returned by list operations |
| CLI output limit | `1,000,000` chars | Maximum gh CLI output retained in memory |
| Estimate range | `0.25–9999` | Valid numeric range for time estimates in hours |
| Estimate granularity | `0.25` | Minimum increment for estimate values (quarter-hour) |
