import api from '../api/axios';
import type {MatchPage, MatchRun} from '../types/match.types';
export const matchService = {
    async list(includeArchived = false, offset = 0): Promise<MatchPage> {
        return (await api.get<MatchPage>('/matches', {params: {include_archived: includeArchived, offset, limit: 20}})).data;
    },
    async run(): Promise<MatchRun> {
        return (await api.post<MatchRun>('/matches/run')).data;
    },
};
