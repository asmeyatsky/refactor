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
  Code as CodeIcon,
  Storage as RepoIcon,
  CheckCircle as CheckIcon
} from '@mui/icons-material';

const InputMethodSelection = ({ selectedMethod, onSelect }) => {
  const methods = [
    {
      id: 'code',
      name: 'Code Snippet',
      description: 'Paste or upload a code snippet to migrate',
      icon: CodeIcon,
      color: '#4285f4',
      features: ['Quick migration', 'Single file', 'Instant results']
    },
    {
      id: 'repository',
      name: 'Repository',
      description: 'Import and migrate an entire Git repository',
      icon: RepoIcon,
      color: '#34a853',
      features: ['Full repository', 'Multi-file analysis', 'Pull Request generation']
    }
  ];

  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 500 }}>
        Choose Your Input Method
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Select how you want to provide your code for migration
      </Typography>

      <Grid container spacing={3}>
        {methods.map((method, index) => {
          const Icon = method.icon;
          const isSelected = selectedMethod === method.id;

          return (
            <Grid item xs={12} md={6} key={method.id}>
              <Fade in={true} timeout={300 + index * 100}>
                <Card
                  elevation={isSelected ? 8 : 2}
                  sx={{
                    height: '100%',
                    border: isSelected ? `3px solid ${method.color}` : '3px solid transparent',
                    transition: 'all 0.3s',
                    '&:hover': {
                      elevation: 4,
                      transform: 'translateY(-4px)',
                    },
                    cursor: 'pointer',
                  }}
                >
                  <CardActionArea onClick={() => onSelect(method.id)} sx={{ height: '100%', p: 2 }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Box
                          sx={{
                            width: 60,
                            height: 60,
                            borderRadius: 2,
                            bgcolor: `${method.color}15`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            mr: 2,
                          }}
                        >
                          <Icon sx={{ fontSize: 32, color: method.color }} />
                        </Box>
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {method.name}
                          </Typography>
                        </Box>
                        {isSelected && (
                          <Zoom in={isSelected}>
                            <CheckIcon sx={{ color: method.color, fontSize: 32 }} />
                          </Zoom>
                        )}
                      </Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {method.description}
                      </Typography>
                      <Box component="ul" sx={{ m: 0, pl: 2 }}>
                        {method.features.map((feature) => (
                          <li key={feature}>
                            <Typography variant="body2" color="text.secondary">
                              {feature}
                            </Typography>
                          </li>
                        ))}
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

export default InputMethodSelection;
