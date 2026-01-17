// ArchViz AI - Azure Infrastructure
// Deploy with: az deployment sub create --location eastus --template-file main.bicep

targetScope = 'subscription'

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure region for resources')
param location string = 'eastus'

@description('Base name for resources')
param baseName string = 'archvizai'

// Resource group
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: 'rg-${baseName}-${environment}'
  location: location
  tags: {
    environment: environment
    project: 'archviz-ai'
  }
}

// Deploy all resources
module resources 'resources.bicep' = {
  scope: rg
  name: 'archviz-resources'
  params: {
    baseName: baseName
    environment: environment
    location: location
  }
}

// Outputs
output resourceGroupName string = rg.name
output acrName string = resources.outputs.acrName
output acrLoginServer string = resources.outputs.acrLoginServer
output openAiEndpoint string = resources.outputs.openAiEndpoint
output storageAccountName string = resources.outputs.storageAccountName
output containerAppUrl string = resources.outputs.containerAppUrl
output staticWebAppUrl string = resources.outputs.staticWebAppUrl
output staticWebAppName string = resources.outputs.staticWebAppName
