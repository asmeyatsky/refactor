import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Card,
  CardContent,
  Grid,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Alert,
  MenuItem as MuiMenuItem,
  List,
  ListItem,
  ListItemText,
  Divider,
  CircularProgress
} from '@mui/material';
import { CloudUpload as CloudUploadIcon, Code as CodeIcon, ContentCopy as ContentCopyIcon, Check as CheckIcon } from '@mui/icons-material';
import { initiateMigration, getMigrationStatus } from './api/client';

const App = () => {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedSection, setCopiedSection] = useState(null);

  const supportedServices = [
    { value: 's3', label: 'S3 to Cloud Storage' },
    { value: 'lambda', label: 'Lambda to Cloud Functions' },
    { value: 'dynamodb', label: 'DynamoDB to Firestore' },
    { value: 'sqs', label: 'SQS to Pub/Sub' },
    { value: 'sns', label: 'SNS to Pub/Sub' },
    { value: 'rds', label: 'RDS to Cloud SQL' },
    { value: 'ec2', label: 'EC2 to Compute Engine' },
    { value: 'cloudwatch', label: 'CloudWatch to Cloud Monitoring' },
    { value: 'apigateway', label: 'API Gateway to Apigee' },
    { value: 'eks', label: 'EKS to GKE' },
    { value: 'fargate', label: 'Fargate to Cloud Run' },
    { value: 'blob_storage', label: 'Azure Blob Storage to Cloud Storage' },
    { value: 'functions', label: 'Azure Functions to Cloud Functions' },
    { value: 'cosmos_db', label: 'Azure Cosmos DB to Firestore' },
    { value: 'service_bus', label: 'Azure Service Bus to Pub/Sub' },
    { value: 'event_hubs', label: 'Azure Event Hubs to Pub/Sub' },
  ];

  const handleAddService = () => {
    if (selectedService && !services.includes(selectedService)) {
      setServices([...services, selectedService]);
    }
    setSelectedService('');
  };

  const handleRemoveService = (service) => {
    setServices(services.filter(s => s !== service));
  };

  const handleMigrate = async () => {
    if (!code) {
      setError('Please enter code to refactor');
      return;
    }

    if (services.length === 0) {
      setError('Please select at least one service to migrate');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Call the backend API to initiate migration
      const response = await initiateMigration(code, language, services);
      const migrationId = response.migration_id;

      // Poll for migration status
      let status = response.status;
      let result = null;

      // Check status immediately first time
      const initialStatus = await getMigrationStatus(migrationId);
      status = initialStatus.status;
      result = initialStatus.result;

      // If still in progress, poll periodically
      while (status === 'in_progress') {
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
        const statusResponse = await getMigrationStatus(migrationId);
        status = statusResponse.status;
        result = statusResponse.result;
      }

      if (status === 'completed') {
        setResult(result);
      } else if (status === 'failed') {
        setError(result?.error || 'Migration failed');
      }
    } catch (err) {
      setError(err.message || 'Migration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleExampleSelect = (exampleCode) => {
    setCode(exampleCode);
  };

  const handleCopyToClipboard = async (text, section) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedSection(section);
      setTimeout(() => setCopiedSection(null), 2000); // Reset after 2 seconds
    } catch (err) {
      console.error('Failed to copy:', err);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setCopiedSection(section);
        setTimeout(() => setCopiedSection(null), 2000);
      } catch (fallbackErr) {
        console.error('Fallback copy failed:', fallbackErr);
      }
      document.body.removeChild(textArea);
    }
  };

  return (
    <div>
      <AppBar position="static">
        <Toolbar>
          <CodeIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Universal Cloud Refactor Agent
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Cloud Service Migration
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Select cloud services to migrate from AWS/Azure to GCP
                </Typography>

                <Box sx={{ mt: 2 }}>
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Select Language</InputLabel>
                    <Select
                      value={language}
                      label="Select Language"
                      onChange={(e) => setLanguage(e.target.value)}
                    >
                      <MenuItem value="python">Python</MenuItem>
                      <MenuItem value="java">Java</MenuItem>
                    </Select>
                  </FormControl>

                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <FormControl fullWidth>
                      <InputLabel>Service to Migrate</InputLabel>
                      <Select
                        value={selectedService}
                        label="Service to Migrate"
                        onChange={(e) => {
                          const serviceValue = e.target.value;
                          setSelectedService(serviceValue);
                          // Auto-add service when selected
                          if (serviceValue && !services.includes(serviceValue)) {
                            setServices([...services, serviceValue]);
                            setSelectedService(''); // Reset dropdown
                          }
                        }}
                      >
                        {supportedServices.map((service) => (
                          <MuiMenuItem key={service.value} value={service.value}>
                            {service.label}
                          </MuiMenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <Button 
                      variant="outlined" 
                      onClick={handleAddService}
                      disabled={!selectedService || services.includes(selectedService)}
                      sx={{ height: '56px' }}
                    >
                      Add
                    </Button>
                  </Box>

                  {services.length > 0 && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle1">Selected Services:</Typography>
                      <Paper sx={{ p: 2, maxHeight: 150, overflow: 'auto' }}>
                        <List>
                          {services.map((service) => {
                            const serviceObj = supportedServices.find(s => s.value === service);
                            return (
                              <ListItem key={service} secondaryAction={
                                <Button 
                                  size="small" 
                                  color="error" 
                                  onClick={() => handleRemoveService(service)}
                                >
                                  Remove
                                </Button>
                              }>
                                <ListItemText primary={serviceObj?.label || service} />
                              </ListItem>
                            );
                          })}
                        </List>
                      </Paper>
                    </Box>
                  )}

                  <Box sx={{ position: 'relative', mb: 2 }}>
                    <TextField
                      fullWidth
                      label="Code to Refactor"
                      multiline
                      rows={15}
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      variant="outlined"
                    />
                    <Box sx={{ position: 'absolute', top: 8, right: 8, display: 'flex', gap: 1 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={copiedSection === 'input' ? <CheckIcon /> : <ContentCopyIcon />}
                        onClick={() => handleCopyToClipboard(code, 'input')}
                        disabled={!code.trim()}
                      >
                        Copy
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        onClick={() => setCode('')}
                        disabled={!code.trim()}
                      >
                        Delete
                      </Button>
                    </Box>
                  </Box>

                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Button
                      variant="contained"
                      startIcon={<CloudUploadIcon />}
                      onClick={handleMigrate}
                      disabled={loading || services.length === 0 || !code.trim()}
                      fullWidth
                    >
                      {loading ? 'Migrating...' : 'Migrate to GCP'}
                    </Button>
                    {loading && <CircularProgress size={24} />}
                  </Box>
                  {services.length === 0 && (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      Please select at least one service to migrate from the dropdown above.
                    </Alert>
                  )}
                  {services.length > 0 && !code.trim() && (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      Please enter code to refactor in the text area above.
                    </Alert>
                  )}
                </Box>

                {error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {error}
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Example Code Snippets
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Select example code to refactor
                </Typography>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS S3 example
s3_client = boto3.client('s3')

# Upload file to S3
s3_client.upload_file('local_file.txt', 'my-bucket', 'remote_file.txt')

# Download file from S3
s3_client.download_file('my-bucket', 'remote_file.txt', 'downloaded_file.txt')

# List objects in bucket
response = s3_client.list_objects_v2(Bucket='my-bucket')
for obj in response.get('Contents', []):
    print(obj['Key'])`)}
                  >
                    S3 to Cloud Storage
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS Lambda example
lambda_client = boto3.client('lambda')

# Invoke a Lambda function
response = lambda_client.invoke(
    FunctionName='my-function',
    InvocationType='RequestResponse',
    Payload='{\"key\": \"value\"}'
)

# Create a Lambda function
lambda_client.create_function(
    FunctionName='my-new-function',
    Runtime='python3.9',
    Role='arn:aws:iam::123456789012:role/lambda-role',
    Handler='lambda_function.lambda_handler',
    Code={'ZipFile': b'fileb://function.zip'}
)`)}
                  >
                    Lambda to Cloud Functions
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS DynamoDB example
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MyTable')

# Put an item
table.put_item(
   Item={
        'id': '123',
        'name': 'John Doe',
        'email': 'john@example.com'
    }
)

# Get an item
response = table.get_item(Key={'id': '123'})
item = response['Item']

# Query items
response = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('id').eq('123')
)`)}
                  >
                    DynamoDB to Firestore
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS SQS example
sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/123456789012/my-queue'

# Send message to queue
response = sqs.send_message(
    QueueUrl=queue_url,
    DelaySeconds=10,
    MessageAttributes={
        'Title': {
            'DataType': 'String',
            'StringValue': 'The Whistler'
        },
        'Author': {
            'DataType': 'String',
            'StringValue': 'John Grisham'
        }
    },
    MessageBody=(
        'Information about current NY Times fiction bestseller for '
        'week of 12/11/2016.'
    )
)

# Receive message from queue
response = sqs.receive_message(
    QueueUrl=queue_url,
    AttributeNames=['SentTimestamp'],
    MaxNumberOfMessages=1,
    MessageAttributeNames=['All'],
    VisibilityTimeoutSeconds=30,
    WaitTimeSeconds=0
)`)}
                  >
                    SQS to Pub/Sub
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS SNS example
sns = boto3.client('sns')

# Publish a message
response = sns.publish(
    TopicArn='arn:aws:sns:us-east-1:123456789012:my-topic',
    Message='Hello World!',
    Subject='Test Message'
)

# Create a topic
response = sns.create_topic(Name='my-topic')`)}
                  >
                    SNS to Pub/Sub
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS RDS example
rds = boto3.client('rds')

# Create a DB instance
response = rds.create_db_instance(
    DBInstanceIdentifier='mydbinstance',
    DBInstanceClass='db.t2.micro',
    Engine='mysql',
    MasterUsername='admin',
    MasterUserPassword='password',
    AllocatedStorage=20
)

# Describe DB instances
response = rds.describe_db_instances()`)}
                  >
                    RDS to Cloud SQL
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS EC2 example
ec2 = boto3.client('ec2')

# Launch an instance
response = ec2.run_instances(
    ImageId='ami-12345678',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.micro'
)

# Describe instances
response = ec2.describe_instances()`)}
                  >
                    EC2 to Compute Engine
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3
from datetime import datetime, timedelta

# AWS CloudWatch example
cloudwatch = boto3.client('cloudwatch')

# Put metric data
cloudwatch.put_metric_data(
    Namespace='MyApplication',
    MetricData=[
        {
            'MetricName': 'PageViews',
            'Value': 123.0,
            'Unit': 'Count'
        }
    ]
)

# Get metric statistics
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow(),
    Period=300,
    Statistics=['Average']
)`)}
                  >
                    CloudWatch to Cloud Monitoring
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS API Gateway example
apigateway = boto3.client('apigateway')

# Create a REST API
response = apigateway.create_rest_api(
    name='my-rest-api',
    description='My test API'
)
api_id = response['id']

# Get APIs
response = apigateway.get_rest_apis()`)}
                  >
                    API Gateway to Apigee
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS EKS example
eks = boto3.client('eks')

# Create a cluster
response = eks.create_cluster(
    name='my-cluster',
    roleArn='arn:aws:iam::123456789012:role/eks-service-role',
    resourcesVpcConfig={
        'subnetIds': [
            'subnet-12345',
            'subnet-67890'
        ]
    }
)

# List clusters
response = eks.list_clusters()`)}
                  >
                    EKS to GKE
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# AWS Fargate example (using ECS)
ecs = boto3.client('ecs')

# Run a task
response = ecs.run_task(
    cluster='my-cluster',
    taskDefinition='my-task-definition',
    count=1,
    startedBy='example'
)`)}
                  >
                    Fargate to Cloud Run
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import boto3

# Azure Blob Storage example
from azure.storage.blob import BlobServiceClient

# Create a blob service client
blob_service_client = BlobServiceClient(
    account_url="https://myaccount.blob.core.windows.net",
    credential="my_account_key"
)

# Upload a file
container_client = blob_service_client.get_container_client("mycontainer")
with open("local_file.txt", "rb") as data:
    container_client.upload_blob(name="remote_file.txt", data=data)

# Download a file
with open("download_file.txt", "wb") as my_blob:
    blob_data = container_client.download_blob("remote_file.txt")
    blob_data.readinto(my_blob)`)}
                  >
                    Azure Blob to Cloud Storage
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import azure.functions as func

# Azure Functions example
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )`)}
                  >
                    Azure Functions to Cloud Functions
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import azure.cosmos

# Azure Cosmos DB example
import azure.cosmos.cosmos_client as cosmos_client

# Initialize the client
client = cosmos_client.CosmosClient(url_connection='https://myaccount.documents.azure.com:443/', auth={'masterKey': 'mykey'})

# Get database
database = client.GetDatabase('my-database')

# Get container
container = client.GetContainer(database['id'], 'my-container')

# Create an item
item = {
    'id': '123',
    'name': 'John Doe',
    'email': 'john@example.com'
}
container.CreateItem(body=item)`)}
                  >
                    Azure Cosmos DB to Firestore
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import azure.servicebus

# Azure Service Bus example
from azure.servicebus import ServiceBusClient, ServiceBusMessage

# Create a Service Bus client
servicebus_client = ServiceBusClient.from_connection_string(conn_str="my_connection_string")

# Send a message
with servicebus_client:
    sender = servicebus_client.get_queue_sender(queue_name="myqueue")
    with sender:
        message = ServiceBusMessage("Hello World!")
        sender.send_messages(message)`)}
                  >
                    Azure Service Bus to Pub/Sub
                  </Button>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleExampleSelect(`import azure.eventhub

# Azure Event Hubs example
from azure.eventhub import EventHubProducerClient, EventData

# Create an Event Hub client
producer = EventHubProducerClient.from_connection_string(
    conn_str="Endpoint=sb://myeventhub.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=secretkey",
    eventhub_name="myeventhub"
)

# Send event
with producer:
    event_data_batch = producer.create_batch()
    event_data_batch.add(EventData('First event'))
    producer.send_batch(event_data_batch)`)}
                  >
                    Azure Event Hubs to Pub/Sub
                  </Button>
                </Box>
              </CardContent>
            </Card>

            {result && (
              <Grid item xs={12}>
                <Card sx={{ mt: 3 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Migration Result
                    </Typography>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2"><strong>Migration ID:</strong> {result.migration_id}</Typography>
                      <Typography variant="body2"><strong>Plan ID:</strong> {result.plan_id || 'N/A'}</Typography>
                      <Typography variant="body2"><strong>Completed at:</strong> {result.completed_at ? new Date(result.completed_at).toLocaleString() : 'N/A'}</Typography>
                      <Typography variant="body2">
                        <strong>Verification:</strong> 
                        <span style={{ color: result.verification_result?.success ? 'green' : 'red', marginLeft: '8px' }}>
                          {result.verification_result?.success ? '✓ PASSED' : '✗ FAILED'}
                        </span>
                      </Typography>
                      <Typography variant="body2">
                        <strong>Security Validation:</strong> 
                        <span style={{ color: result.security_validation_passed ? 'green' : 'red', marginLeft: '8px' }}>
                          {result.security_validation_passed ? '✓ PASSED' : '✗ FAILED'}
                        </span>
                      </Typography>
                    </Box>
                    
                    {result.execution_result?.service_results && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>Service Migration Results:</Typography>
                        {Object.entries(result.execution_result.service_results).map(([service, stats]) => (
                          <Typography key={service} variant="body2" sx={{ ml: 2 }}>
                            • {service}: {stats.success || 0} successful, {stats.failed || 0} failed
                          </Typography>
                        ))}
                      </Box>
                    )}

                    {result.refactored_code && (
                      <Box sx={{ mt: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2">Refactored Code:</Typography>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                              size="small"
                              startIcon={copiedSection === 'refactored' ? <CheckIcon /> : <ContentCopyIcon />}
                              onClick={() => handleCopyToClipboard(result.refactored_code, 'refactored')}
                              variant="outlined"
                              color={copiedSection === 'refactored' ? 'success' : 'primary'}
                            >
                              {copiedSection === 'refactored' ? 'Copied!' : 'Copy'}
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              onClick={() => setResult({...result, refactored_code: null})}
                            >
                              Delete
                            </Button>
                          </Box>
                        </Box>
                        <Paper sx={{ p: 2, bgcolor: '#f5f5f5', maxHeight: 400, overflow: 'auto', position: 'relative' }}>
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                            {result.refactored_code}
                          </pre>
                        </Paper>
                      </Box>
                    )}
                    
                    {result.variable_mapping && Object.keys(result.variable_mapping).length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Variable Name Changes Report:
                        </Typography>
                        <Paper sx={{ p: 2, bgcolor: '#e3f2fd', maxHeight: 300, overflow: 'auto' }}>
                          <Typography variant="body2" component="div">
                            <strong>Summary:</strong> The following variable names were changed during migration. 
                            Update these throughout your codebase for consistency.
                          </Typography>
                          <Box component="ul" sx={{ mt: 1, pl: 3 }}>
                            {Object.entries(result.variable_mapping).map(([oldName, newName]) => (
                              <li key={oldName} style={{ marginBottom: '8px' }}>
                                <code style={{ backgroundColor: '#fff', padding: '2px 6px', borderRadius: '3px' }}>
                                  {oldName}
                                </code>
                                {' → '}
                                <code style={{ backgroundColor: '#fff', padding: '2px 6px', borderRadius: '3px' }}>
                                  {newName}
                                </code>
                              </li>
                            ))}
                          </Box>
                        </Paper>
                      </Box>
                    )}

                    {result.code && !result.refactored_code && (
                      <Box sx={{ mt: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2">Original Code:</Typography>
                          <Button
                            size="small"
                            startIcon={copiedSection === 'original' ? <CheckIcon /> : <ContentCopyIcon />}
                            onClick={() => handleCopyToClipboard(result.code, 'original')}
                            variant="outlined"
                            color={copiedSection === 'original' ? 'success' : 'primary'}
                          >
                            {copiedSection === 'original' ? 'Copied!' : 'Copy Code'}
                          </Button>
                        </Box>
                        <Paper sx={{ p: 2, bgcolor: '#f5f5f5', maxHeight: 400, overflow: 'auto' }}>
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                            {result.code}
                          </pre>
                        </Paper>
                        <Alert severity="info" sx={{ mt: 1 }}>
                          Note: Refactored code will appear here once migration completes. Check the migration status for details.
                        </Alert>
                      </Box>
                    )}

                    {result.errors && result.errors.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Alert severity="error">
                          <Typography variant="subtitle2">Errors:</Typography>
                          <ul style={{ marginTop: '8px', paddingLeft: '20px' }}>
                            {result.errors.map((error, idx) => (
                              <li key={idx}>{error}</li>
                            ))}
                          </ul>
                        </Alert>
                      </Box>
                    )}

                    {result.warnings && result.warnings.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Alert severity="warning">
                          <Typography variant="subtitle2">Warnings:</Typography>
                          <ul style={{ marginTop: '8px', paddingLeft: '20px' }}>
                            {result.warnings.map((warning, idx) => (
                              <li key={idx}>{warning}</li>
                            ))}
                          </ul>
                        </Alert>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        </Grid>
      </Container>
    </div>
  );
};

export default App;