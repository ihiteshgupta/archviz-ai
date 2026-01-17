// ArchViz AI - Azure Resources

@description('Base name for resources')
param baseName string

@description('Environment')
param environment string

@description('Location')
param location string

@description('Location for Azure OpenAI (must support GPT-4o and DALL-E 3)')
param openAiLocation string = 'swedencentral'

// Unique suffix for globally unique names (shortened for storage account limits)
var uniqueSuffix = substring(uniqueString(resourceGroup().id), 0, 8)
var resourcePrefix = '${baseName}${substring(environment, 0, 1)}'  // e.g., archvizaid

// =============================================================================
// Azure Container Registry
// =============================================================================
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acr${baseName}${uniqueSuffix}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
  tags: {
    environment: environment
  }
}

// =============================================================================
// Azure OpenAI Service
// =============================================================================
resource openAi 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: 'oai-${resourcePrefix}-${uniqueSuffix}'
  location: openAiLocation  // Use dedicated region for OpenAI (supports DALL-E 3)
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: 'oai-${resourcePrefix}-${uniqueSuffix}'
    publicNetworkAccess: 'Enabled'
  }
  tags: {
    environment: environment
  }
}

// GPT-4o Deployment
resource gpt4Deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openAi
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 30  // TPM in thousands
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-05-13'
    }
  }
}

// DALL-E 3 Deployment
resource dalleDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openAi
  name: 'dall-e-3'
  sku: {
    name: 'Standard'
    capacity: 1
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'dall-e-3'
      version: '3.0'
    }
  }
  dependsOn: [gpt4Deployment]  // Sequential deployment
}

// =============================================================================
// Storage Account
// =============================================================================
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${resourcePrefix}${uniqueSuffix}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
  tags: {
    environment: environment
  }
}

// Blob service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// Containers
resource uploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'uploads'
  properties: {
    publicAccess: 'None'
  }
}

resource rendersContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'renders'
  properties: {
    publicAccess: 'None'
  }
}

resource texturesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'textures'
  properties: {
    publicAccess: 'None'
  }
}

resource modelsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'models'
  properties: {
    publicAccess: 'None'
  }
}

// =============================================================================
// Container Apps Environment
// =============================================================================
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${resourcePrefix}-${uniqueSuffix}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-${resourcePrefix}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
  tags: {
    environment: environment
  }
}

// Container App for API
resource apiContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-${resourcePrefix}-api'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      secrets: [
        {
          name: 'openai-key'
          value: openAi.listKeys().key1
        }
        {
          name: 'storage-connection'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'  // Placeholder
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: openAi.properties.endpoint
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'openai-key'
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection'
            }
            {
              name: 'AZURE_OPENAI_GPT4_DEPLOYMENT'
              value: 'gpt-4o'
            }
            {
              name: 'AZURE_OPENAI_DALLE_DEPLOYMENT'
              value: 'dall-e-3'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 5
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
  tags: {
    environment: environment
  }
}

// =============================================================================
// Static Web App for Frontend
// =============================================================================
resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: 'swa-${resourcePrefix}'
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    buildProperties: {
      appLocation: '/frontend'
      outputLocation: '.next'
      appBuildCommand: 'npm run build'
    }
  }
  tags: {
    environment: environment
  }
}

// =============================================================================
// Cosmos DB (for production persistence)
// =============================================================================
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = if (environment == 'prod') {
  name: 'cosmos-${resourcePrefix}-${uniqueSuffix}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
  tags: {
    environment: environment
  }
}

// =============================================================================
// Outputs
// =============================================================================
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output openAiEndpoint string = openAi.properties.endpoint
output openAiName string = openAi.name
output storageAccountName string = storageAccount.name
output containerAppUrl string = 'https://${apiContainerApp.properties.configuration.ingress.fqdn}'
output staticWebAppUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output staticWebAppName string = staticWebApp.name
output containerAppsEnvId string = containerAppsEnv.id
