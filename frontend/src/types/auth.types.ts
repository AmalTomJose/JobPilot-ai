import {z} from "zod";
import { loginSchema } from "../schemas/auth.schema";
import { registerSchema } from "../schemas/auth.schema";
import type  {User}  from "../types/user.types";

export type LoginFormData = z.infer<typeof loginSchema>;

export type RegisterFormData = z.infer<typeof registerSchema>;


export type LoginResponse = {
    access_token: string;
    token_type: string;
    user: User;
};