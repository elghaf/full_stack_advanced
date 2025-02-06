// src/services/apiClient.ts
import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api",
});

export default apiClient;