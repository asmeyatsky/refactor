import React, { useState, useRef, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Card,
  CardContent,
  Stepper,
  Step,
  StepLabel,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Chip,
  Fade,
  Zoom,
  Slide
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Code as CodeIcon,
  Storage as StorageIcon,
  AutoAwesome as AutoAwesomeIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as RadioButtonUncheckedIcon
} from '@mui/icons-material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import CloudProviderSelection from './components/CloudProviderSelection';
import InputMethodSelection from './components/InputMethodSelection';
import CodeSnippetInput from './components/CodeSnippetInput';
import RepositoryInput from './components/RepositoryInput';
import MigrationResults from './components/MigrationResults';
import { analyzeRepository, migrateRepository, migrateCodeSnippet, getMigrationStatus } from './api/client';

const theme = createTheme({
  palette: {
    primary: {
      main: '#4285f4', // Google Blue
    },
    secondary: {
      main: '#34a853', // Google Green
    },
    background: {
      default: '#f8f9fa',
    },
  },
  typography: {
    fontFamily: '"Google Sans", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 500,
    },
    h5: {
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 12,
  },
});

const steps = ['Select Cloud Provider', 'Choose Input Method', 'Provide Code/Repository', 'Review & Refactor'];

const App = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [cloudProvider, setCloudProvider] = useState(null); // 'aws' or 'azure'
  const [inputMethod, setInputMethod] = useState(null); // 'code' or 'repository'
  const [codeSnippet, setCodeSnippet] = useState('');
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [repositoryBranch, setRepositoryBranch] = useState('main');
  const [selectedServices, setSelectedServices] = useState([]);
  const [language, setLanguage] = useState('python');
  const [migrationResult, setMigrationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  
  // Refs to store interval and timeout IDs for cleanup
  const pollIntervalRef = useRef(null);
  const timeoutRef = useRef(null);
  
  // Cleanup intervals and timeouts on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, []);

  const handleNext = () => {
    if (activeStep === 0 && !cloudProvider) {
      setError('Please select a cloud provider');
      return;
    }
    if (activeStep === 1 && !inputMethod) {
      setError('Please select an input method');
      return;
    }
    if (activeStep === 2) {
      if (inputMethod === 'code' && !codeSnippet.trim()) {
        setError('Please provide code to refactor');
        return;
      }
      if (inputMethod === 'repository' && !repositoryUrl.trim()) {
        setError('Please provide a repository URL');
        return;
      }
    }
    setError(null);
    setActiveStep((prevStep) => prevStep + 1);
  };

  const handleBack = () => {
    setError(null);
    setActiveStep((prevStep) => prevStep - 1);
  };

  const handleReset = () => {
    // Cleanup any running intervals/timeouts
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    
    setActiveStep(0);
    setCloudProvider(null);
    setInputMethod(null);
    setCodeSnippet('');
    setRepositoryUrl('');
    setRepositoryBranch('main');
    setSelectedServices([]);
    setLanguage('python');
    setMigrationResult(null);
    setError(null);
    setAnalysisResult(null);
    setLoading(false);
  };

  const handleAnalyzeRepository = async () => {
    if (!repositoryUrl.trim()) {
      setError('Please provide a repository URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await analyzeRepository(repositoryUrl, repositoryBranch);
      setAnalysisResult(result);
      // Auto-select services from analysis
      if (result.mar && result.mar.services_detected) {
        const services = result.mar.services_detected.map(s => s.service_name);
        setSelectedServices(services);
      }
    } catch (err) {
      setError(err.message || 'Failed to analyze repository');
    } finally {
      setLoading(false);
    }
  };

  const handleMigrate = async () => {
    // Clear any existing intervals/timeouts before starting a new migration
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    
    setLoading(true);
    setError(null);
    setMigrationResult(null);

    try {
      let result;
      if (inputMethod === 'code') {
        // Start migration and get migration_id
        const initialResponse = await migrateCodeSnippet({
          code: codeSnippet,
          language,
          services: selectedServices,
          cloudProvider
        });
        
        // Poll for completion
        const migrationId = initialResponse.migration_id;
        if (migrationId) {
          // Poll every 1 second until completed
          pollIntervalRef.current = setInterval(async () => {
            try {
              const statusResponse = await getMigrationStatus(migrationId);
              
              if (statusResponse.status === 'completed') {
                // Cleanup
                if (pollIntervalRef.current) {
                  clearInterval(pollIntervalRef.current);
                  pollIntervalRef.current = null;
                }
                if (timeoutRef.current) {
                  clearTimeout(timeoutRef.current);
                  timeoutRef.current = null;
                }
                // Extract refactored code and format result
                const finalResult = {
                  success: true,
                  refactored_code: statusResponse.refactored_code || statusResponse.result?.refactored_code,
                  variable_mapping: statusResponse.variable_mapping || statusResponse.result?.variable_mapping,
                  migration_id: migrationId,
                  ...statusResponse.result
                };
                setMigrationResult(finalResult);
                setActiveStep(3);
                setLoading(false);
              } else if (statusResponse.status === 'failed') {
                // Cleanup
                if (pollIntervalRef.current) {
                  clearInterval(pollIntervalRef.current);
                  pollIntervalRef.current = null;
                }
                if (timeoutRef.current) {
                  clearTimeout(timeoutRef.current);
                  timeoutRef.current = null;
                }
                setError(statusResponse.result?.error || 'Refactoring failed');
                setLoading(false);
              }
              // If still pending or in_progress, continue polling
            } catch (pollError) {
              console.error('Polling error:', pollError);
              // Continue polling on error
            }
          }, 1000); // Poll every 1 second
          
          // Set timeout after 5 minutes (300 seconds) to allow for Gemini API calls and processing
          timeoutRef.current = setTimeout(() => {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setError('Refactoring timeout - please check the refactoring status manually');
            setLoading(false);
          }, 300000); // 5 minutes
        } else {
          // Fallback if no migration_id
          setMigrationResult(initialResponse);
          setActiveStep(3);
          setLoading(false);
        }
      } else {
        // Repository migration
        if (!analysisResult || !analysisResult.repository_id) {
          setError('Please analyze the repository first');
          setLoading(false);
          return;
        }
        result = await migrateRepository({
          repositoryId: analysisResult.repository_id,
          services: selectedServices,
          createPR: false
        });
        console.log('App.js - Migration result received:', result);
        console.log('App.js - refactored_files:', result?.refactored_files);
        console.log('App.js - files_changed:', result?.files_changed);
        setMigrationResult(result);
        setActiveStep(3);
        setLoading(false);
      }
    } catch (err) {
      // Cleanup on error
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      setError(err.message || 'Refactoring failed');
      setLoading(false);
    }
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <CloudProviderSelection
            selectedProvider={cloudProvider}
            onSelect={setCloudProvider}
          />
        );
      case 1:
        return (
          <InputMethodSelection
            selectedMethod={inputMethod}
            onSelect={setInputMethod}
          />
        );
      case 2:
        if (inputMethod === 'code') {
          return (
            <CodeSnippetInput
              code={codeSnippet}
              language={language}
              onCodeChange={setCodeSnippet}
              onLanguageChange={setLanguage}
              cloudProvider={cloudProvider}
              selectedServices={selectedServices}
              onServicesChange={setSelectedServices}
            />
          );
        } else {
          return (
            <RepositoryInput
              repositoryUrl={repositoryUrl}
              branch={repositoryBranch}
              onUrlChange={setRepositoryUrl}
              onBranchChange={setRepositoryBranch}
              onAnalyze={handleAnalyzeRepository}
              analysisResult={analysisResult}
              loading={loading}
              cloudProvider={cloudProvider}
              selectedServices={selectedServices}
              onServicesChange={setSelectedServices}
            />
          );
        }
      case 3:
        return (
          <MigrationResults
            result={migrationResult}
            inputMethod={inputMethod}
            cloudProvider={cloudProvider}
            onReset={handleReset}
          />
        );
      default:
        return null;
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <AppBar position="static" elevation={0} sx={{ bgcolor: 'transparent', backdropFilter: 'blur(10px)' }}>
          <Toolbar>
            <AutoAwesomeIcon sx={{ mr: 2, color: 'white' }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1, color: 'white', fontWeight: 500 }}>
              Universal Cloud Refactor Agent
            </Typography>
            {cloudProvider && (
              <Chip
                label={cloudProvider.toUpperCase()}
                sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white', fontWeight: 500 }}
              />
            )}
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Fade in={true} timeout={800}>
            <Card elevation={8} sx={{ borderRadius: 3, overflow: 'hidden' }}>
              <Box sx={{ bgcolor: 'primary.main', color: 'white', p: 3 }}>
                <Typography variant="h4" gutterBottom sx={{ fontWeight: 500 }}>
                  Cloud Migration Assistant
                </Typography>
                <Typography variant="body1" sx={{ opacity: 0.9 }}>
                  Transform your {cloudProvider ? cloudProvider.toUpperCase() : 'cloud'} infrastructure to Google Cloud Platform
                </Typography>
              </Box>

              <CardContent sx={{ p: 4 }}>
                <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
                  {steps.map((label, index) => (
                    <Step key={label}>
                      <StepLabel
                        StepIconComponent={({ active, completed }) => (
                          <Box
                            sx={{
                              width: 40,
                              height: 40,
                              borderRadius: '50%',
                              bgcolor: completed || active ? 'primary.main' : 'grey.300',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: 'white',
                              fontWeight: 'bold',
                              transition: 'all 0.3s',
                            }}
                          >
                            {completed ? <CheckCircleIcon /> : index + 1}
                          </Box>
                        )}
                      >
                        {label}
                      </StepLabel>
                    </Step>
                  ))}
                </Stepper>

                {error && (
                  <Slide direction="down" in={!!error}>
                    <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
                      {error}
                    </Alert>
                  </Slide>
                )}

                <Box sx={{ minHeight: 400 }}>
                  {renderStepContent()}
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
                  <Button
                    disabled={activeStep === 0}
                    onClick={handleBack}
                    sx={{ minWidth: 120 }}
                  >
                    Back
                  </Button>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    {activeStep === steps.length - 1 ? (
                      <Button
                        variant="contained"
                        onClick={handleReset}
                        startIcon={<AutoAwesomeIcon />}
                        sx={{ minWidth: 150 }}
                      >
                        New Refactoring
                      </Button>
                    ) : activeStep === 2 ? (
                      <Button
                        variant="contained"
                        onClick={handleMigrate}
                        disabled={loading || (inputMethod === 'code' && !codeSnippet.trim()) || 
                                 (inputMethod === 'repository' && (!repositoryUrl.trim() || !analysisResult))}
                        startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <CloudUploadIcon />}
                        sx={{ minWidth: 150 }}
                      >
                        {loading ? 'Refactoring...' : 'Start Refactoring'}
                      </Button>
                    ) : (
                      <Button
                        variant="contained"
                        onClick={handleNext}
                        disabled={
                          (activeStep === 0 && !cloudProvider) ||
                          (activeStep === 1 && !inputMethod)
                        }
                        sx={{ minWidth: 120 }}
                      >
                        Next
                      </Button>
                    )}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Fade>
        </Container>
      </div>
    </ThemeProvider>
  );
};

export default App;
