import api from "../api/axios";
import type { ResumeResponse } from "../types/resume.types";
export const resumeService = {
    uploadResume: async (file: File): Promise<ResumeResponse> => {
        const formData = new FormData();
        formData.append("file", file);
        const response = await api.post<ResumeResponse>("/resume/upload", formData);
        return response.data;
    },
};
