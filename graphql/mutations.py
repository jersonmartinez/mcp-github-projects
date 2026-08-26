"""GraphQL mutation strings for GitHub Projects V2 API.

Contains write operations for updating fields, archiving items,
creating custom fields, and adding items to projects. These mutations
are used by the ProjectService and FieldService to modify project
state via the GitHub GraphQL API.
"""

UPDATE_FIELD_MUTATION: str = """
mutation UpdateField($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: $value
  }) {
    projectV2Item {
      id
    }
  }
}
""".strip()

ARCHIVE_ITEM_MUTATION: str = """
mutation ArchiveItem($projectId: ID!, $itemId: ID!) {
  archiveProjectV2Item(input: {
    projectId: $projectId
    itemId: $itemId
  }) {
    item {
      id
    }
  }
}
""".strip()

CREATE_FIELD_MUTATION: str = """
mutation CreateField($projectId: ID!, $name: String!, $dataType: ProjectV2CustomFieldType!) {
  createProjectV2Field(input: {
    projectId: $projectId
    name: $name
    dataType: $dataType
  }) {
    projectV2Field {
      ... on ProjectV2Field {
        id
        name
        dataType
      }
      ... on ProjectV2SingleSelectField {
        id
        name
        dataType
      }
      ... on ProjectV2IterationField {
        id
        name
        dataType
      }
    }
  }
}
""".strip()

ADD_ITEM_TO_PROJECT_MUTATION: str = """
mutation AddItemToProject($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {
    projectId: $projectId
    contentId: $contentId
  }) {
    item {
      id
    }
  }
}
""".strip()
