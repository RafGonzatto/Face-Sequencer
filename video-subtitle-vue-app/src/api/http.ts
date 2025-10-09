import axios, { AxiosResponse, AxiosError } from 'axios';

const baseURL = import.meta.env.VITE_API_BASE || '/api';

export const api = axios.create({
  baseURL,
  timeout: 30000,
});

api.interceptors.response.use(
  (r: AxiosResponse) => r,
  (err: AxiosError<any>) => {
    const data: any = err.response?.data;
    return Promise.reject({
      message: data?.error || data?.message || err.message,
      status: err.response?.status,
      details: data?.details,
      raw: err,
    });
  }
);

export default api;
