import api from "../api/axios";
import type { ResumeResponse } from "../types/resume.types";
import type { ResumeParse, ResumeSummary } from '../types/resume-parse.types';
export const resumeService = {
    async list(): Promise<ResumeSummary[]> { return (await api.get<ResumeSummary[]>('/resume')).data; },
    async get(id: number): Promise<ResumeResponse> { return (await api.get<ResumeResponse>(`/resume/${id}`)).data; },
    async getParse(id: number): Promise<ResumeParse> { return (await api.get<ResumeParse>(`/resume/${id}/parse`)).data; },
    async parse(id: number, force = false): Promise<ResumeParse> { return (await api.post<ResumeParse>(`/resume/${id}/parse`, null, {params: {force}})).data; },
    uploadResume: async (file: File): Promise<ResumeResponse> => {
        const formData = new FormData();
        formData.append("file", file);
        const response = await api.post<ResumeResponse>("/resume/upload", formData);
        return response.data;
    },
};
