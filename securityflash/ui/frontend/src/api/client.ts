import axios from 'axios';
import { API_BASE } from '../config';

let authToken: string | null = null;

export const setAuthToken = (token: string | null) => {
  authToken = token;
};

export const apiClient = axios.create({
  baseURL: API_BASE
});

apiClient.interceptors.request.use((config) => {
  if (authToken) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

export default apiClient;
