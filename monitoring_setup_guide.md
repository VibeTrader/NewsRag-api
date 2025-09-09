# Setting up Monitoring for NewsRagnarok API

This guide will help you set up and configure monitoring for the NewsRagnarok API deployed in Azure App Service.

## Prerequisites

1. Azure account with access to the App Service
2. Permissions to create/modify Application Insights resources
3. Access to Azure Portal

## Step 1: Enable Application Insights (If not already enabled)

1. **In Azure Portal**:
   - Navigate to your App Service
   - In the left sidebar, select "Application Insights"
   - Click "Turn on Application Insights" if not already enabled
   - Create a new Application Insights resource or select an existing one
   - Select "Recommended" for the collection level
   - Click "Apply"

2. **Configure application settings**:
   - In the App Service, go to "Configuration" > "Application settings"
   - Ensure the following settings are present:
     - `APPINSIGHTS_INSTRUMENTATIONKEY`: Your Application Insights instrumentation key
     - `ApplicationInsightsAgent_EXTENSION_VERSION`: `~3` (to enable the extension)
     - `XDT_MicrosoftApplicationInsights_Mode`: `recommended`

## Step 2: Create a Monitoring Dashboard

1. **In Azure Portal**:
   - Go to "Dashboard" in the left sidebar
   - Click "New Dashboard"
   - Name it "NewsRagnarok API Monitoring"

2. **Add Key Metrics**:
   - Click "Edit" on the dashboard
   - From the tile gallery, add "Application Insights" metrics tiles
   - Configure each tile with the queries from `monitoring_queries.kql`
   - Arrange tiles in a logical order (Performance, Business, Errors, etc.)
   - Save the dashboard

## Step 3: Set Up Alerts

1. **Create Alert Rules**:
   - Go to your Application Insights resource
   - Select "Alerts" from the left sidebar
   - Click "Create" > "Alert rule"

2. **Configure these essential alerts**:

   **API Availability Alert**:
   - Select "Availability" as the signal type
   - Condition: Less than 99% availability over 5 minutes
   - Set appropriate action group (email, SMS, etc.)

   **Error Rate Alert**:
   - Select "Custom log search" as the signal type
   - Query:
     ```kql
     requests
     | where success == false
     | summarize count() by bin(timestamp, 5m)
     ```
   - Condition: Count > 5 errors in 5 minutes
   - Set appropriate action group

   **Response Time Alert**:
   - Select "Custom metric" as the signal type
   - Metric: "summary_total_time"
   - Condition: Average > 10000 (10 seconds) over 5 minutes
   - Set appropriate action group

   **Dependency Failure Alert**:
   - Select "Custom log search" as the signal type
   - Query:
     ```kql
     dependencies
     | where success == false
     | summarize count() by bin(timestamp, 5m)
     ```
   - Condition: Count > 3 in 5 minutes
   - Set appropriate action group

## Step 4: Set Up Log Analytics Workspace

1. **Create or Select Log Analytics Workspace**:
   - Go to "Log Analytics workspaces" in Azure Portal
   - Create a new workspace or select an existing one
   - Link your Application Insights resource to this workspace

2. **Configure Data Retention**:
   - Set appropriate retention period (default is 30 days)
   - Consider longer retention for critical metrics

## Step 5: Set Up Workbooks for Advanced Analysis

1. **Create Custom Workbooks**:
   - In your Application Insights resource, go to "Workbooks"
   - Create a new workbook for each major area:
     - **Search Performance Workbook**: Detailed analysis of search operations
     - **Summarization Workbook**: In-depth metrics on summary generation
     - **Dependency Performance Workbook**: Analysis of external dependencies
     - **Error Analysis Workbook**: Detailed error troubleshooting

2. **Add the KQL queries** from `monitoring_queries.kql` to each workbook

## Step 6: Regular Monitoring Review

Establish a routine for reviewing monitoring data:

1. **Daily Check**: Review dashboard for any anomalies or errors
2. **Weekly Review**: Analyze performance trends and usage patterns
3. **Monthly Analysis**: Comprehensive review of all metrics and alerts
4. **Quarterly Optimization**: Adjust thresholds and add new metrics as needed

## Additional Considerations

1. **Cost Management**:
   - Monitor the data volume being collected
   - Adjust sampling rate if needed
   - Consider using Capacity Reservations for predictable billing

2. **Performance Impact**:
   - Application Insights has minimal impact on performance
   - Consider adjusting instrumentation level if needed

3. **Security**:
   - Ensure access to monitoring data is properly restricted
   - Consider using Private Link for Application Insights

4. **Export and Integration**:
   - Set up continuous export to Azure Storage for long-term analytics
   - Consider integration with Power BI for executive dashboards

## Troubleshooting

1. **Missing Data**:
   - Verify instrumentation key is correctly set
   - Check network connectivity from the app to Application Insights
   - Verify data sampling settings

2. **High Data Volume**:
   - Adjust sampling rate
   - Filter unnecessary telemetry
   - Optimize custom event tracking

3. **Alert Fatigue**:
   - Review and adjust alert thresholds
   - Implement alert suppression for maintenance periods
   - Use action groups effectively to route alerts to appropriate teams
