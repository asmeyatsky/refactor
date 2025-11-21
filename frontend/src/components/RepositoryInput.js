import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Grid,
  Fade
} from '@mui/material';
import { Autocomplete } from '@mui/material';
import {
  Search as SearchIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Storage as StorageIcon,
  Code as CodeIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { Autocomplete } from '@mui/material';

const RepositoryInput = ({
  repositoryUrl,
  branch,
  onUrlChange,
  onBranchChange,
  onAnalyze,
  analysisResult,
  loading,
  cloudProvider,
  selectedServices,
  onServicesChange
}) => {
  const [urlError, setUrlError] = useState('');

  const validateUrl = (url) => {
    if (!url.trim()) {
      setUrlError('');
      return false;
    }
    const patterns = [
      /^https?:\/\/github\.com\/[\w\-\.]+\/[\w\-\.]+/,
      /^https?:\/\/gitlab\.com\/[\w\-\.]+\/[\w\-\.]+/,
      /^https?:\/\/bitbucket\.org\/[\w\-\.]+\/[\w\-\.]+/,
      /^git@github\.com:[\w\-\.]+\/[\w\-\.]+/,
      /^git@gitlab\.com:[\w\-\.]+\/[\w\-\.]+/,
    ];
    const isValid = patterns.some(pattern => pattern.test(url));
    if (!isValid) {
      setUrlError('Please enter a valid GitHub, GitLab, or Bitbucket URL');
    } else {
      setUrlError('');
    }
    return isValid;
  };

  const handleUrlChange = (e) => {
    const url = e.target.value;
    onUrlChange(url);
    validateUrl(url);
  };

  const services = analysisResult?.mar?.services_detected || [];
  const availableServices = services.map(s => ({
    value: s.service_name,
    label: `${s.service_name} (${s.service_type}) - ${s.files_affected.length} files`
  }));

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 500 }}>
        Import Repository
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Provide your Git repository URL to analyze and migrate
      </Typography>

      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          label="Repository URL"
          placeholder="https://github.com/user/repo.git"
          value={repositoryUrl}
          onChange={handleUrlChange}
          error={!!urlError}
          helperText={urlError || 'GitHub, GitLab, or Bitbucket repository URL'}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          label="Branch"
          value={branch}
          onChange={(e) => onBranchChange(e.target.value)}
          placeholder="main"
          sx={{ mb: 2 }}
        />
        <Button
          variant="contained"
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
          onClick={onAnalyze}
          disabled={loading || !repositoryUrl.trim() || !!urlError}
          fullWidth
          sx={{ mb: 2 }}
        >
          {loading ? 'Analyzing...' : 'Analyze Repository'}
        </Button>
      </Box>

      {analysisResult && analysisResult.mar && (
        <Fade in={!!analysisResult}>
          <Paper elevation={2} sx={{ p: 3, bgcolor: 'success.light', bgcolor: 'rgba(76, 175, 80, 0.1)' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <CheckIcon color="success" sx={{ mr: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Analysis Complete
              </Typography>
            </Box>

            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <CodeIcon sx={{ mr: 1, color: 'text.secondary' }} />
                  <Typography variant="body2">
                    <strong>Files:</strong> {analysisResult.mar.total_files}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <StorageIcon sx={{ mr: 1, color: 'text.secondary' }} />
                  <Typography variant="body2">
                    <strong>Lines:</strong> {analysisResult.mar.total_lines.toLocaleString()}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <AssessmentIcon sx={{ mr: 1, color: 'text.secondary' }} />
                  <Typography variant="body2">
                    <strong>Services:</strong> {analysisResult.mar.services_detected.length}
                  </Typography>
                </Box>
                <Typography variant="body2">
                  <strong>Confidence:</strong> {(analysisResult.mar.confidence_score * 100).toFixed(1)}%
                </Typography>
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
              Detected Services
            </Typography>
            <List dense>
              {services.slice(0, 5).map((service) => (
                <ListItem key={service.service_name}>
                  <ListItemIcon>
                    <CheckIcon color="success" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary={service.service_name}
                    secondary={`${service.files_affected.length} files • ${service.service_type.toUpperCase()}`}
                  />
                </ListItem>
              ))}
              {services.length > 5 && (
                <ListItem>
                  <ListItemText
                    primary={`+${services.length - 5} more services`}
                    primaryTypographyProps={{ color: 'text.secondary' }}
                  />
                </ListItem>
              )}
            </List>

            {availableServices.length > 0 && (
              <Box sx={{ mt: 3 }}>
                <Autocomplete
                  multiple
                  options={availableServices}
                  getOptionLabel={(option) => typeof option === 'string' ? option : option.label}
                  value={selectedServices.map(s => availableServices.find(svc => svc.value === s) || s)}
                  onChange={(event, newValue) => {
                    onServicesChange(newValue.map(v => typeof v === 'string' ? v : v.value));
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Select Services to Migrate"
                      placeholder="All services selected by default"
                    />
                  )}
                  renderTags={(value, getTagProps) =>
                    value.map((option, index) => {
                      const service = typeof option === 'string' 
                        ? availableServices.find(s => s.value === option)
                        : option;
                      return (
                        <Chip
                          {...getTagProps({ index })}
                          key={service?.value || option}
                          label={service?.value || option}
                          color="primary"
                          variant="outlined"
                          size="small"
                        />
                      );
                    })
                  }
                />
              </Box>
            )}
          </Paper>
        </Fade>
      )}

      {analysisResult && !analysisResult.mar && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Analysis completed but no services were detected. The repository may not contain cloud service code.
        </Alert>
      )}
    </Box>
  );
};

export default RepositoryInput;
