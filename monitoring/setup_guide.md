# Setting Up Azure Application Insights for NewsRagnarok API

This guide will help you set up Azure Application Insights to monitor your NewsRagnarok API deployed on Azure App Service.

## Prerequisites
- Azure subscription
- NewsRagnarok API deployed on Azure App Service
- Access to the Azure Portal

## Step 1: Create an Application Insights Resource

1. Log in to the [Azure Portal](https://portal.azure.com)
2. Click "Create a resource"
3. Search for "Application Insights" and select it
4. Click "Create"
5. Fill in the following details:
   - **Subscription**: Select your subscription
   - **Resource Group**: Select the same resource group as your App Service
   - **Name**: NewsRagnarok-AppInsights (or your preferred name)
   - **Region**: Select the same region as your App Service
   - **Resource Mode**: Workspace-based
6. Click "Review + create", then "Create"
7. Wait for the deployment to complete, then click "Go to resource"

## Step 2: Get the Instrumentation Key

1. In your Application Insights resource, find the "Instrumentation Key" in the overview page
2. Copy this key, you'll need it in the next step

## Step 3: Configure Your App Service

1. Go to your App Service in the Azure Portal
2. In the left sidebar, click on "Configuration"
3. Click on "New application setting"
4. Add the following settings:
   - **Name**: APPINSIGHTS_INSTRUMENTATIONKEY
   - **Value**: Paste the instrumentation key you copied
5. Click "OK"
6. Click "Save" at the top of the configuration page
7. Wait for the app to restart

## Step 4: Deploy the Updated API Code

1. Deploy the updated NewsRagnarok API code that includes the Application Insights integration
2. Ensure the requirements.txt file includes the Application Insights packages

## Step 5: Import the Dashboard

1. In the Azure Portal, click on "Dashboard" in the left sidebar
2. Click "New Dashboard" → "Upload"
3. Locate the `dashboard_template.json` file from the monitoring folder
4. Before uploading, edit the file and replace "{appInsightsResourceId}" with your actual App Insights resource ID
   - Resource ID format: `/subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/microsoft.insights/components/{app-insights-name}`
5. Upload the edited file
6. Save the dashboard

## Step 6: Create Basic Alert Rules

1. Go to your Application Insights resource
2. In the left sidebar, click on "Alerts"
3. Click "Create" → "Alert rule"
4. Set up the following alerts:

### API Availability Alert
- **Condition**: Availability < 99%
- **Evaluation frequency**: 5 minutes
- **Severity**: 1 (Critical)

### Failed Requests Alert
- **Condition**: Failed requests > 5 in 5 minutes
- **Evaluation frequency**: 5 minutes
- **Severity**: 2 (Warning)

### Response Time Alert
- **Condition**: Server response time > 5 seconds
- **Evaluation frequency**: 5 minutes
- **Severity**: 2 (Warning)

### Exception Rate Alert
- **Condition**: Exceptions > 3 in 5 minutes
- **Evaluation frequency**: 5 minutes
- **Severity**: 2 (Warning)

## Step 7: Set Up Action Groups for Alerts

1. In the Azure Portal, go to "Monitor"
2. Click on "Alerts" in the left sidebar
3. Click on "Action groups"
4. Click "Add action group"
5. Configure the action group:
   - **Name**: NewsRagnarok-AlertGroup
   - **Short name**: NewsRagAPI
   - Add email, SMS, or webhook notifications as needed
6. Click "Review + create", then "Create"
7. Assign this action group to each of your alert rules

## Step 8: Configure Log Analytics

1. In your Application Insights resource, click on "Logs" in the left sidebar
2. Use the following sample queries to analyze your API:

### Search Performance Query
```
customMetrics
| where name == "search_latency"
| summarize avg(value) by bin(timestamp, 1h)
| render timechart
```

### Summary Performance Query
```
customMetrics
| where name == "summary_generation_time" 
| summarize avg(value) by bin(timestamp, 1h)
| render timechart
```

### Error Analysis Query
```
exceptions
| where timestamp > ago(24h)
| summarize count() by operation_Name, bin(timestamp, 1h)
| render barchart
```

## Next Steps

1. **Monitor Regularly**: Check your dashboard daily for the first week
2. **Refine Alerts**: Adjust threshold values based on observed patterns
3. **Expand Metrics**: Add more custom metrics as needed
4. **Set Up Availability Tests**: Configure URL ping tests to monitor API health
5. **Configure Continuous Export**: Set up continuous export to Azure Storage for long-term analysis