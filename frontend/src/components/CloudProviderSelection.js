import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Grid,
  Fade,
  Chip
} from '@mui/material';
import {
  CloudQueue as AWSIcon,
  CloudQueue as AzureIcon,
  CheckCircle as CheckIcon
} from '@mui/icons-material';

const CloudProviderSelection = ({ selectedProvider, onSelect }) => {
  const providers = [
    {
      id: 'aws',
      name: 'Amazon Web Services (AWS)',
      description: 'Migrate from AWS services to Google Cloud Platform',
      icon: AWSIcon,
      color: '#FF9900',
      services: ['S3', 'Lambda', 'DynamoDB', 'SQS', 'SNS', 'RDS', 'EC2', 'CloudWatch', 'API Gateway', 'EKS', 'Fargate', 'ElastiCache']
    },
    {
      id: 'azure',
      name: 'Microsoft Azure',
      description: 'Migrate from Azure services to Google Cloud Platform',
      icon: AzureIcon,
      color: '#0078D4',
      services: ['Blob Storage', 'Functions', 'Cosmos DB', 'Service Bus', 'Event Hubs', 'SQL Database', 'Virtual Machines', 'Monitor', 'API Management', 'Redis Cache', 'AKS', 'Container Instances', 'App Service', 'Key Vault', 'Application Insights']
    }
  ];

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ mb: 2, fontWeight: 500 }}>
        Select Source Cloud Provider
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Choose the cloud provider you want to migrate from to Google Cloud Platform
      </Typography>

      <Grid container spacing={3}>
        {providers.map((provider) => {
          const Icon = provider.icon;
          const isSelected = selectedProvider === provider.id;
          
          return (
            <Grid item xs={12} md={6} key={provider.id}>
              <Fade in={true} timeout={500}>
                <Card
                  elevation={isSelected ? 8 : 2}
                  sx={{
                    height: '100%',
                    border: isSelected ? `3px solid ${provider.color}` : '3px solid transparent',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: 6
                    }
                  }}
                >
                  <CardActionArea onClick={() => onSelect(provider.id)} sx={{ height: '100%' }}>
                    <CardContent sx={{ p: 3 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Box
                          sx={{
                            width: 56,
                            height: 56,
                            borderRadius: '50%',
                            bgcolor: provider.color,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            mr: 2
                          }}
                        >
                          <Icon sx={{ color: 'white', fontSize: 32 }} />
                        </Box>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                            {provider.name}
                          </Typography>
                          {isSelected && (
                            <Chip
                              icon={<CheckIcon />}
                              label="Selected"
                              color="primary"
                              size="small"
                              sx={{ mt: 0.5 }}
                            />
                          )}
                        </Box>
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {provider.description}
                      </Typography>

                      <Box sx={{ mt: 2 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block', fontWeight: 600 }}>
                          Supported Services ({provider.services.length}):
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {provider.services.slice(0, 6).map((service) => (
                            <Chip
                              key={service}
                              label={service}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.7rem' }}
                            />
                          ))}
                          {provider.services.length > 6 && (
                            <Chip
                              label={`+${provider.services.length - 6} more`}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.7rem' }}
                            />
                          )}
                        </Box>
                      </Box>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Fade>
            </Grid>
          );
        })}
      </Grid>

      {selectedProvider && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="body2" color="primary.main" sx={{ fontWeight: 500 }}>
            ✓ {providers.find(p => p.id === selectedProvider)?.name} selected
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default CloudProviderSelection;
