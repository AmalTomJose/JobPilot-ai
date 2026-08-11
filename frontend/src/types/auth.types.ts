import {z} from "zod";
import { loginSchema } from "../schemas/auth.schema";
import { registerSchema } from "../schemas/auth.schema";

export type LoginFormData = z.infer<typeof loginSchema>;

export type RegisterFormData = z.infer<typeof registerSchema>;

