'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box, Button, Flex, FormControl, FormLabel, Input,
  VStack, Heading, Alert, AlertIcon, FormErrorMessage
} from '@chakra-ui/react';

export default function RegisterPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || data.error || 'Registration failed');
      } else {
        router.push('/sign-in');
      }
    } catch (err) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Flex align="center" justify="center" height="100vh" bg="gray.50">
      <Box w="lg" p={8} bg="white" boxShadow="lg" borderRadius="md">
        <Heading mb={6} textAlign="center">Register</Heading>
        <form onSubmit={handleSubmit}>
          <VStack spacing={4} align="stretch">
            {error && (
              <Alert status="error">
                <AlertIcon />{error}
              </Alert>
            )}
            <FormControl isRequired>
              <FormLabel>Username</FormLabel>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
              />
            </FormControl>
            <FormControl isRequired>
              <FormLabel>Email</FormLabel>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter email"
              />
            </FormControl>
            <FormControl isRequired>
              <FormLabel>Password</FormLabel>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
              />
            </FormControl>
            <FormControl isRequired isInvalid={!!error && password !== confirm}>
              <FormLabel>Confirm Password</FormLabel>
              <Input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Confirm password"
              />
              {password !== confirm && (
                <FormErrorMessage>Passwords must match</FormErrorMessage>
              )}
            </FormControl>
            <Button
              type="submit"
              colorScheme="blue"
              isLoading={loading}
            >
              Register
            </Button>
          </VStack>
        </form>
      </Box>
    </Flex>
  );
} 