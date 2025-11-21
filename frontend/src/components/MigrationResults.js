import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  LinearProgress
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  ContentCopy as CopyIcon,
  Check as CheckedIcon,
  Download as DownloadIcon,
  AutoAwesome as AutoAwesomeIcon
} from '@mui/icons-material';

const MigrationResults = ({ result, inputMethod, cloudProvider, onReset }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  if (!result) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Processing migration...
        </Typography>
      </Box>
    );
  }

  const isSuccess = result.success !== false;
  const hasErrors = result.errors && result.errors.length > 0;
  const hasWarnings = result.warnings && result.warnings.length > 0;

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 4 }}>
        {isSuccess ? (
          <CheckIcon sx={{ fontSize: 48, color: 'success.main', mr: 2 }} />
        ) : (
          <ErrorIcon sx={{ fontSize: 48, color: 'error.main', mr: 2 }} />
        )}
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>
            {isSuccess ? 'Migration Completed!' : 'Migration Completed with Issues'}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {inputMethod === 'code' 
              ? 'Your code has been migrated to Google Cloud Platform'
              : 'Your repository migration has been processed'}
          </Typography>
        </Box>
      </Box>

      {result.test_results && (
        <Paper elevation={2} sx={{ p: 3, mb: 3, bgcolor: result.test_results.success ? 'success.light' : 'warning.light' }}>
          <Typography variant="h6" gutterBottom>
            Test Results ({result.test_results.framework})
          </Typography>
          <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
            <Box>
              <Typography variant="body2" color="text.secondary">Total</Typography>
              <Typography variant="h6">{result.test_results.total_tests}</Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">Passed</Typography>
              <Typography variant="h6" color="success.main">{result.test_results.passed}</Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">Failed</Typography>
              <Typography variant="h6" color="error.main">{result.test_results.failed}</Typography>
            </Box>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={(result.test_results.passed / result.test_results.total_tests) * 100} 
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Paper>
      )}

      {result.files_changed && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Migration Summary
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Chip label={`${result.total_files_changed || result.files_changed.length} Files Changed`} color="primary" />
            {result.total_files_failed > 0 && (
              <Chip label={`${result.total_files_failed} Failed`} color="error" />
            )}
          </Box>
        </Paper>
      )}

      {result.refactored_code && (
        <Accordion defaultExpanded sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Refactored Code
              </Typography>
              <Tooltip title={copied ? 'Copied!' : 'Copy code'}>
                <IconButton
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCopy(result.refactored_code);
                  }}
                  size="small"
                >
                  {copied ? <CheckedIcon color="success" /> : <CopyIcon />}
                </IconButton>
              </Tooltip>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Paper
              sx={{
                p: 2,
                bgcolor: '#f5f5f5',
                maxHeight: 500,
                overflow: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
              }}
            >
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{result.refactored_code}</pre>
            </Paper>
          </AccordionDetails>
        </Accordion>
      )}

      {result.variable_mapping && Object.keys(result.variable_mapping).length > 0 && (
        <Accordion sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Variable Mappings</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box component="ul" sx={{ m: 0, pl: 2 }}>
              {Object.entries(result.variable_mapping).map(([oldName, newName]) => (
                <li key={oldName} style={{ marginBottom: '8px' }}>
                  <code style={{ backgroundColor: '#f5f5f5', padding: '2px 6px', borderRadius: '3px' }}>
                    {oldName}
                  </code>
                  {' → '}
                  <code style={{ backgroundColor: '#e3f2fd', padding: '2px 6px', borderRadius: '3px' }}>
                    {newName}
                  </code>
                </li>
              ))}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasErrors && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Errors:</Typography>
          <Box component="ul" sx={{ m: 0, pl: 2 }}>
            {result.errors.map((error, idx) => (
              <li key={idx}>{error}</li>
            ))}
          </Box>
        </Alert>
      )}

      {hasWarnings && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Warnings:</Typography>
          <Box component="ul" sx={{ m: 0, pl: 2 }}>
            {result.warnings.map((warning, idx) => (
              <li key={idx}>{warning}</li>
            ))}
          </Box>
        </Alert>
      )}

      {result.pr_url && (
        <Alert severity="success" sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Pull Request Created:</Typography>
          <Button
            href={result.pr_url}
            target="_blank"
            rel="noopener noreferrer"
            variant="outlined"
            size="small"
            sx={{ mt: 1 }}
          >
            View Pull Request
          </Button>
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <Button
          variant="contained"
          size="large"
          startIcon={<AutoAwesomeIcon />}
          onClick={onReset}
          sx={{ minWidth: 200 }}
        >
          Start New Migration
        </Button>
      </Box>
    </Box>
  );
};

export default MigrationResults;
