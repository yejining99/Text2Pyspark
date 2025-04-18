# DataHub GraphQL 쿼리 모음

ROOT_GLOSSARY_NODES_QUERY = """
query getRootGlossaryNodes {
  getRootGlossaryNodes(input: {start: 0, count: 1000}) {
    count
    start
    total
    nodes {
      ...rootGlossaryNodeWithFourLayers
      __typename
    }
    __typename
  }
}

fragment rootGlossaryNodeWithFourLayers on GlossaryNode {
  urn
  type
  properties {
    name
    description
    __typename
  }
  displayProperties {
    ...displayPropertiesFields
    __typename
  }
  children: relationships(
    input: {types: ["IsPartOf"], direction: INCOMING, start: 0, count: 500}
  ) {
    total
    relationships {
      type
      entity {
        type
        ... on GlossaryTerm {
          urn
          __typename
        }
        ... on GlossaryNode {
          urn
          children: relationships(
            input: {types: ["IsPartOf"], direction: INCOMING, start: 0, count: 500}
          ) {
            total
            relationships {
              type
              entity {
                type
                ... on GlossaryTerm {
                  urn
                  __typename
                }
                ... on GlossaryNode {
                  urn
                  children: relationships(
                    input: {types: ["IsPartOf"], direction: INCOMING, start: 0, count: 500}
                  ) {
                    total
                    relationships {
                      type
                      entity {
                        type
                        ... on GlossaryTerm {
                          urn
                          __typename
                        }
                        ... on GlossaryNode {
                          urn
                          children: relationships(
                            input: {types: ["IsPartOf"], direction: INCOMING, start: 0, count: 500}
                          ) {
                            total
                            relationships {
                              type
                              entity {
                                type
                                ... on GlossaryTerm {
                                  urn
                                  __typename
                                }
                                ... on GlossaryNode {
                                  urn
                                  __typename
                                }
                                __typename
                              }
                              __typename
                            }
                            __typename
                          }
                          __typename
                        }
                        __typename
                      }
                      __typename
                    }
                    __typename
                  }
                  __typename
                }
                __typename
              }
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}

fragment displayPropertiesFields on DisplayProperties {
  colorHex
  icon {
    name
    style
    iconLibrary
    __typename
  }
  __typename
}
"""

GLOSSARY_NODE_QUERY = """
query getGlossaryNode($urn: String!) {
  glossaryNode(urn: $urn) {
    urn
    type
    exists
    properties {
      name
      description
      __typename
    }
    ownership {
      ...ownershipFields
      __typename
    }
    parentNodes {
      ...parentNodesFields
      __typename
    }
    privileges {
      ...entityPrivileges
      __typename
    }
    autoRenderAspects: aspects(input: {autoRenderOnly: true}) {
      ...autoRenderAspectFields
      __typename
    }
    structuredProperties {
      properties {
        ...structuredPropertiesFields
        __typename
      }
      __typename
    }
    forms {
      ...formsFields
      __typename
    }
    children: relationships(
      input: {types: ["IsPartOf"], direction: INCOMING, start: 0, count: 10000}
    ) {
      total
      relationships {
        direction
        entity {
          type
          urn
          ... on GlossaryNode {
            ...glossaryNode
            __typename
          }
          ... on GlossaryTerm {
            ...childGlossaryTerm
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    displayProperties {
      ...displayPropertiesFields
      __typename
    }
    ...notes
    __typename
  }
}

fragment ownershipFields on Ownership {
  owners {
    owner {
      ... on CorpUser {
        urn
        type
        username
        info {
          active
          displayName
          title
          email
          firstName
          lastName
          fullName
          __typename
        }
        properties {
          active
          displayName
          title
          email
          firstName
          lastName
          fullName
          __typename
        }
        editableProperties {
          displayName
          title
          pictureLink
          email
          __typename
        }
        __typename
      }
      ... on CorpGroup {
        urn
        type
        name
        properties {
          displayName
          email
          __typename
        }
        info {
          displayName
          email
          admins {
            urn
            username
            info {
              active
              displayName
              title
              email
              firstName
              lastName
              fullName
              __typename
            }
            editableInfo {
              pictureLink
              teams
              skills
              __typename
            }
            __typename
          }
          members {
            urn
            username
            info {
              active
              displayName
              title
              email
              firstName
              lastName
              fullName
              __typename
            }
            editableInfo {
              pictureLink
              teams
              skills
              __typename
            }
            __typename
          }
          groups
          __typename
        }
        __typename
      }
      __typename
    }
    type
    ownershipType {
      urn
      type
      info {
        name
        description
        __typename
      }
      status {
        removed
        __typename
      }
      __typename
    }
    associatedUrn
    __typename
  }
  lastModified {
    time
    __typename
  }
  __typename
}

fragment parentNodesFields on ParentNodesResult {
  count
  nodes {
    urn
    type
    properties {
      name
      __typename
    }
    displayProperties {
      ...displayPropertiesFields
      __typename
    }
    __typename
  }
  __typename
}

fragment displayPropertiesFields on DisplayProperties {
  colorHex
  icon {
    name
    style
    iconLibrary
    __typename
  }
  __typename
}

fragment entityPrivileges on EntityPrivileges {
  canEditLineage
  canEditDomains
  canEditDataProducts
  canEditTags
  canEditGlossaryTerms
  canEditDescription
  canEditLinks
  canEditOwners
  canEditAssertions
  canEditIncidents
  canEditDeprecation
  canEditSchemaFieldTags
  canEditSchemaFieldGlossaryTerms
  canEditSchemaFieldDescription
  canEditQueries
  canEditEmbed
  canManageEntity
  canManageChildren
  canEditProperties
  canViewDatasetUsage
  canViewDatasetProfile
  canViewDatasetOperations
  __typename
}

fragment autoRenderAspectFields on RawAspect {
  aspectName
  payload
  renderSpec {
    displayType
    displayName
    key
    __typename
  }
  __typename
}

fragment structuredPropertiesFields on StructuredPropertiesEntry {
  structuredProperty {
    exists
    ...structuredPropertyFields
    __typename
  }
  values {
    ... on StringValue {
      stringValue
      __typename
    }
    ... on NumberValue {
      numberValue
      __typename
    }
    __typename
  }
  valueEntities {
    urn
    type
    ...entityDisplayNameFields
    __typename
  }
  associatedUrn
  __typename
}

fragment structuredPropertyFields on StructuredPropertyEntity {
  urn
  type
  definition {
    displayName
    qualifiedName
    description
    cardinality
    immutable
    valueType {
      urn
      type
      info {
        type
        displayName
        __typename
      }
      __typename
    }
    entityTypes {
      urn
      type
      info {
        type
        __typename
      }
      __typename
    }
    cardinality
    typeQualifier {
      allowedTypes {
        urn
        type
        info {
          type
          displayName
          __typename
        }
        __typename
      }
      __typename
    }
    allowedValues {
      value {
        ... on StringValue {
          stringValue
          __typename
        }
        ... on NumberValue {
          numberValue
          __typename
        }
        __typename
      }
      description
      __typename
    }
    created {
      time
      actor {
        urn
        editableProperties {
          displayName
          pictureLink
          __typename
        }
        ...entityDisplayNameFields
        __typename
      }
      __typename
    }
    lastModified {
      time
      actor {
        urn
        editableProperties {
          displayName
          pictureLink
          __typename
        }
        ...entityDisplayNameFields
        __typename
      }
      __typename
    }
    __typename
  }
  settings {
    isHidden
    showInSearchFilters
    showAsAssetBadge
    showInAssetSummary
    showInColumnsTable
    __typename
  }
  __typename
}

fragment entityDisplayNameFields on Entity {
  urn
  type
  ... on Dataset {
    name
    properties {
      name
      qualifiedName
      __typename
    }
    __typename
  }
  ... on CorpUser {
    username
    properties {
      displayName
      title
      firstName
      lastName
      fullName
      email
      __typename
    }
    info {
      active
      displayName
      title
      firstName
      lastName
      fullName
      email
      __typename
    }
    __typename
  }
  ... on CorpGroup {
    name
    info {
      displayName
      __typename
    }
    __typename
  }
  ... on Dashboard {
    dashboardId
    properties {
      name
      __typename
    }
    __typename
  }
  ... on Chart {
    chartId
    properties {
      name
      __typename
    }
    __typename
  }
  ... on DataFlow {
    properties {
      name
      __typename
    }
    __typename
  }
  ... on DataJob {
    jobId
    properties {
      name
      __typename
    }
    __typename
  }
  ... on GlossaryTerm {
    name
    hierarchicalName
    properties {
      name
      __typename
    }
    __typename
  }
  ... on GlossaryNode {
    properties {
      name
      description
      __typename
    }
    __typename
  }
  ... on Domain {
    properties {
      name
      __typename
    }
    __typename
  }
  ... on Container {
    properties {
      name
      __typename
    }
    __typename
  }
  ... on MLFeatureTable {
    name
    __typename
  }
  ... on MLFeature {
    name
    __typename
  }
  ... on MLPrimaryKey {
    name
    __typename
  }
  ... on MLModel {
    name
    __typename
  }
  ... on MLModelGroup {
    name
    __typename
  }
  ... on Tag {
    name
    properties {
      name
      colorHex
      __typename
    }
    __typename
  }
  ... on DataPlatform {
    ...nonConflictingPlatformFields
    __typename
  }
  ... on DataProduct {
    properties {
      name
      __typename
    }
    __typename
  }
  ... on DataPlatformInstance {
    instanceId
    __typename
  }
  ... on StructuredPropertyEntity {
    definition {
      displayName
      qualifiedName
      __typename
    }
    __typename
  }
  ... on SchemaFieldEntity {
    fieldPath
    __typename
  }
  ... on OwnershipTypeEntity {
    info {
      name
      __typename
    }
    __typename
  }
  __typename
}

fragment nonConflictingPlatformFields on DataPlatform {
  urn
  type
  name
  properties {
    displayName
    datasetNameDelimiter
    logoUrl
    __typename
  }
  displayName
  info {
    type
    displayName
    datasetNameDelimiter
    logoUrl
    __typename
  }
  __typename
}

fragment formsFields on Forms {
  completedForms {
    ...formAssociationFields
    __typename
  }
  incompleteForms {
    ...formAssociationFields
    __typename
  }
  verifications {
    form {
      urn
      __typename
    }
    lastModified {
      time
      actor {
        urn
        type
        ...entityDisplayNameFields
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}

fragment formAssociationFields on FormAssociation {
  associatedUrn
  incompletePrompts {
    ...formPromptAssociationFields
    __typename
  }
  completedPrompts {
    ...formPromptAssociationFields
    __typename
  }
  form {
    urn
    type
    info {
      name
      description
      type
      prompts {
        id
        formUrn
        title
        description
        type
        required
        structuredPropertyParams {
          structuredProperty {
            ...structuredPropertyFields
            __typename
          }
          __typename
        }
        __typename
      }
      actors {
        owners
        isAssignedToMe
        __typename
      }
      __typename
    }
    ownership {
      ...ownershipFields
      __typename
    }
    __typename
  }
  __typename
}

fragment formPromptAssociationFields on FormPromptAssociation {
  id
  lastModified {
    time
    actor {
      urn
      type
      ...entityDisplayNameFields
      __typename
    }
    __typename
  }
  fieldAssociations {
    completedFieldPrompts {
      fieldPath
      lastModified {
        time
        actor {
          urn
          type
          ...entityDisplayNameFields
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}

fragment glossaryNode on GlossaryNode {
  urn
  type
  properties {
    name
    description
    __typename
  }
  displayProperties {
    ...displayPropertiesFields
    __typename
  }
  children: relationships(
    input: {types: ["IsPartOf"], direction: INCOMING, start: 0, count: 1000}
  ) {
    total
    relationships {
      type
      entity {
        ... on GlossaryTerm {
          urn
          name
          type
          hierarchicalName
          properties {
            name
            description
            __typename
          }
          __typename
        }
        ... on GlossaryNode {
          urn
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}

fragment childGlossaryTerm on GlossaryTerm {
  urn
  type
  name
  hierarchicalName
  properties {
    name
    description
    __typename
  }
  __typename
}

fragment notes on Entity {
  notes: relationships(
    input: {types: ["PostTarget"], direction: INCOMING, start: 0, count: 100}
  ) {
    total
    relationships {
      type
      entity {
        ... on Post {
          urn
          type
          postType
          lastModified {
            time
            actor
            __typename
          }
          content {
            contentType
            title
            description
            link
            media {
              type
              location
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}
"""
