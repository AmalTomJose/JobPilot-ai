import api from '../api/axios';
import type {ProfileData} from '../types/profile.types';
export type Section = 'summary'|'skills'|'experience'|'projects'|'education';
export type Statement = {text:string; evidence:string[]};
export type Proposal = {summary:Statement|null; skills:string[]; experience:{source_index:number;bullets:Statement[]}[]; projects:{source_index:number;bullets:Statement[]}[]; section_order:Section[]; changes:string[]; questions:string[]};
export type ResumeVersion = {pdf_filename:string|null;saved_pdf:string|null;id:number;job_id:number;revision:number;status:'generating'|'draft'|'approved'|'failed';profile_revision:number;job_revision:number;profile_snapshot:ProfileData;job_snapshot:{title:string;company:string|null;description:string};data:ProfileData|null;proposal:Proposal|null;section_order:Section[];model:string;prompt_version:string;error:string|null;stale:boolean;created_at:string;approved_at:string|null};
export type VersionList = {configured:boolean;profile_revision:number|null;job_revision:number;has_description:boolean;items:{id:number;status:string;created_at:string;error:string|null}[];total:number;offset:number;limit:number};
const base = (jobId:number) => `/jobs/${jobId}/tailoring`;
export const tailoringService = {
    async list(jobId:number,offset=0):Promise<VersionList> {return (await api.get(base(jobId),{params:{offset}})).data;},
    async get(jobId:number,id:number):Promise<ResumeVersion> {return (await api.get(`${base(jobId)}/${id}`)).data;},
    async generate(jobId:number,request_id:string,profile_revision:number,job_revision:number):Promise<ResumeVersion> {return (await api.post(base(jobId),{request_id,profile_revision,job_revision,consent:true},{timeout:90000})).data;},
    async save(jobId:number,id:number,expected_revision:number,data:ProfileData,section_order:Section[],approve:boolean):Promise<ResumeVersion> {return (await api.put(`${base(jobId)}/${id}`,{expected_revision,data,section_order,approve})).data;},
    async discard(jobId:number,id:number,expected_revision:number):Promise<void> {await api.delete(`${base(jobId)}/${id}`,{params:{expected_revision}});},
    async pdf(jobId:number,id:number):Promise<Blob> {return (await api.get(`${base(jobId)}/${id}/pdf`,{responseType:'blob'})).data;},
};
