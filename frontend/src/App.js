import React, { useState } from 'react';
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
import { analyzeRepository, migrateRepository, migrateCodeSnippet } from './api/client';

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

const steps = ['Select Cloud Provider', 'Choose Input Method', 'Provide Code/Repository', 'Review & Migrate'];

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
        setError('Please provide code to migrate');
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
    setLoading(true);
    setError(null);
    setMigrationResult(null);

    try {
      let result;
      if (inputMethod === 'code') {
        result = await migrateCodeSnippet({
          code: codeSnippet,
          language,
          services: selectedServices,
          cloudProvider
        });
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
      }
      setMigrationResult(result);
      setActiveStep(3);
    } catch (err) {
      setError(err.message || 'Migration failed');
    } finally {
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
                        New Migration
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
                        {loading ? 'Migrating...' : 'Start Migration'}
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
