import {z} from 'zod';

export const loginSchema = z.object({
    email:z
    .email("Invalid email adress"),
    password:z
    .string().min(6,"Password must be at least 6 characters long")
})



export const registerSchema = z.object({
    name:z.string().min(2,"Name must be at least 2 characters long"),
    email:z.email("Invalid email adress"),
    password:z.string().min(6,"Password must be at least 6 characters long"),
    confirmPassword:z.string().min(6,"Confirm Password must be at least 6 characters long"),
    acceptTerms:z.boolean().refine((val)=> val === true,{message:"You must accept the terms and conditions"})
}).refine(
    (data)=>data.password === data.confirmPassword,
    {
        path:["confirmPassword"],
        message:"Passwords do not match"
    }
)