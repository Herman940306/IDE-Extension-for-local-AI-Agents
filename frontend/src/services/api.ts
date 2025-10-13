/**
 * API Service for Backend Communication
 * Project Creator: Herman Swanepoel
 */

import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8001';

export class ApiService {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    async getHealth() {
        const response = await axios.get(`${this.baseUrl}/health`);
        return response.data;
    }

    async getApiInfo() {
        const response = await axios.get(`${this.baseUrl}/`);
        return response.data;
    }
}

export const apiService = new ApiService();
