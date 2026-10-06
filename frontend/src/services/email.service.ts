import api from '../api/axios';
import type {GmailStatus, GmailLabel, GmailSelection, EmailPage, SyncRun} from '../types/email.types';
export const emailService = {
    async status(): Promise<GmailStatus> {return (await api.get('/email/gmail')).data;},
    async connect(): Promise<{authorization_url: string}> {return (await api.post('/email/gmail/connect', undefined, {withCredentials: true})).data;},
    async labels(): Promise<GmailLabel[]> {return (await api.get('/email/gmail/labels')).data;},
    async select(selection: GmailSelection): Promise<GmailStatus> {return (await api.put('/email/gmail/selection', selection)).data;},
    async sync(): Promise<SyncRun> {return (await api.post('/email/gmail/sync', undefined, {timeout: 120000})).data;},
    async disconnect(): Promise<{revoked: boolean}> {return (await api.delete('/email/gmail')).data;},
    async messages(offset = 0): Promise<EmailPage> {return (await api.get('/email/gmail/messages', {params: {limit: 20, offset}})).data;},
    async runs(): Promise<SyncRun[]> {return (await api.get('/email/gmail/runs')).data;},
};
