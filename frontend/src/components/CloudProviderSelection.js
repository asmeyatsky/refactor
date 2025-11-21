import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Grid,
  Fade,
  Zoom
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
      name: 'Amazon Web Services',
      shortName: 'AWS',
      description: 'Migrate from AWS services to GCP',
      icon: AWSIcon,
      color: '#FF9900',
      services: ['S3', 'Lambda', 'DynamoDB', 'SQS', 'SNS', 'RDS', 'EC2', 'EKS', 'Fargate']
    },
    {
      id: 'azure',
      name: 'Microsoft Azure',
      shortName: 'Azure',
      description: 'Migrate from Azure services to GCP',
      icon: AzureIcon,
      color: '#0078D4',
      services: ['Blob Storage', 'Functions', 'Cosmos DB', 'Service Bus', 'Event Hubs', 'AKS']
    }
  ];

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 500 }}>
        Select Your Cloud Provider
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Choose the cloud platform you're currently using. We'll help you migrate to Google Cloud Platform.
      </Typography>

      <Grid container spacing={3}>
        {providers.map((provider, index) => {
          const Icon = provider.icon;
          const isSelected = selectedProvider === provider.id;

          return (
            <Grid item xs={12} md={6} key={provider.id}>
              <Fade in={true} timeout={300 + index * 100}>
                <Card
                  elevation={isSelected ? 8 : 2}
                  sx={{
                    height: '100%',
                    border: isSelected ? `3px solid ${provider.color}` : '3px solid transparent',
                    transition: 'all 0.3s',
                    '&:hover': {
                      elevation: 4,
                      transform: 'translateY(-4px)',
                    },
                    cursor: 'pointer',
                  }}
                >
                  <CardActionArea onClick={() => onSelect(provider.id)} sx={{ height: '100%', p: 2 }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Box
                          sx={{
                            width: 60,
                            height: 60,
                            borderRadius: 2,
                            bgcolor: `${provider.color}15`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            mr: 2,
                          }}
                        >
                          <Icon sx={{ fontSize: 32, color: provider.color }} />
                        </Box>
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {provider.shortName}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {provider.name}
                          </Typography>
                        </Box>
                        {isSelected && (
                          <Zoom in={isSelected}>
                            <CheckIcon sx={{ color: provider.color, fontSize: 32 }} />
                          </Zoom>
                        )}
                      </Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {provider.description}
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {provider.services.slice(0, 6).map((service) => (
                          <Box
                            key={service}
                            sx={{
                              px: 1.5,
                              py: 0.5,
                              borderRadius: 1,
                              bgcolor: `${provider.color}10`,
                              color: provider.color,
                              fontSize: '0.75rem',
                              fontWeight: 500,
                            }}
                          >
                            {service}
                          </Box>
                        ))}
                        {provider.services.length > 6 && (
                          <Box
                            sx={{
                              px: 1.5,
                              py: 0.5,
                              borderRadius: 1,
                              bgcolor: 'grey.200',
                              fontSize: '0.75rem',
                              fontWeight: 500,
                            }}
                          >
                            +{provider.services.length - 6} more
                          </Box>
                        )}
                      </Box>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Fade>
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
};

export default CloudProviderSelection;
