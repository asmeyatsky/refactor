import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Paper,
  Button,
  Autocomplete,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  Delete as DeleteIcon,
  UploadFile as UploadIcon
} from '@mui/icons-material';

const CodeSnippetInput = ({
  code,
  language,
  onCodeChange,
  onLanguageChange,
  selectedServices,
  onServicesChange
}) => {
  const [copied, setCopied] = useState(false);

  const services = [
    { value: 's3', label: 'S3 → Cloud Storage' },
    { value: 'lambda', label: 'Lambda → Cloud Functions' },
    { value: 'dynamodb', label: 'DynamoDB → Firestore' },
    { value: 'sqs', label: 'SQS → Pub/Sub' },
    { value: 'sns', label: 'SNS → Pub/Sub' },
    { value: 'rds', label: 'RDS → Cloud SQL' },
    { value: 'ec2', label: 'EC2 → Compute Engine' },
    { value: 'cloudwatch', label: 'CloudWatch → Cloud Monitoring' },
    { value: 'apigateway', label: 'API Gateway → Apigee' },
    { value: 'eks', label: 'EKS → GKE' },
    { value: 'fargate', label: 'Fargate → Cloud Run' },
  ];

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        onCodeChange(e.target.result);
      };
      reader.readAsText(file);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 500 }}>
        Provide Your Code
      </Typography>

      <Box sx={{ mb: 3 }}>
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Programming Language</InputLabel>
          <Select value={language} label="Programming Language" onChange={(e) => onLanguageChange(e.target.value)}>
            <MenuItem value="python">Python</MenuItem>
            <MenuItem value="java">Java</MenuItem>
            <MenuItem value="csharp">C# (.NET)</MenuItem>
            <MenuItem value="javascript">JavaScript / Node.js</MenuItem>
            <MenuItem value="go">Go (Golang)</MenuItem>
          </Select>
        </FormControl>

        <Autocomplete
          multiple
          options={services}
          getOptionLabel={(option) => typeof option === 'string' ? option : option.label}
          value={selectedServices.map(s => services.find(svc => svc.value === s) || s)}
          onChange={(event, newValue) => {
            onServicesChange(newValue.map(v => typeof v === 'string' ? v : v.value));
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Services to Migrate"
              placeholder="Select services..."
            />
          )}
          renderTags={(value, getTagProps) =>
            value.map((option, index) => {
              const service = typeof option === 'string' 
                ? services.find(s => s.value === option)
                : option;
              return (
                <Chip
                  {...getTagProps({ index })}
                  key={service?.value || option}
                  label={service?.label || option}
                  color="primary"
                  variant="outlined"
                />
              );
            })
          }
        />
      </Box>

      <Box sx={{ position: 'relative' }}>
        <TextField
          fullWidth
          label="Code to Migrate"
          multiline
          rows={20}
          value={code}
          onChange={(e) => onCodeChange(e.target.value)}
          variant="outlined"
          sx={{
            '& .MuiInputBase-root': {
              fontFamily: 'monospace',
              fontSize: '0.875rem',
            },
          }}
        />
        <Box sx={{ position: 'absolute', top: 8, right: 8, display: 'flex', gap: 1 }}>
          <input
            accept=".py,.java,.js,.ts,.cs,.csx"
            style={{ display: 'none' }}
            id="file-upload"
            type="file"
            onChange={handleFileUpload}
          />
          <label htmlFor="file-upload">
            <Tooltip title="Upload file">
              <IconButton component="span" size="small">
                <UploadIcon />
              </IconButton>
            </Tooltip>
          </label>
          <Tooltip title={copied ? 'Copied!' : 'Copy code'}>
            <IconButton onClick={handleCopy} size="small" disabled={!code.trim()}>
              {copied ? <CheckIcon color="success" /> : <CopyIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Clear code">
            <IconButton onClick={() => onCodeChange('')} size="small" disabled={!code.trim()}>
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {selectedServices.length === 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            💡 Tip: Select the services you want to migrate from the dropdown above
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default CodeSnippetInput;
