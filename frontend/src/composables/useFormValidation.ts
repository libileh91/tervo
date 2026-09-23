/**
 * Tervo — Zod validation schemas for all forms.
 *
 * Uses Zod (v3) + VeeValidate for frontend form validation.
 * Messages are in French.
 *
 * Usage:
 *   import { useForm } from 'vee-validate'
 *   import { toTypedSchema } from '@vee-validate/zod'
 *   import { loginSchema } from '@/composables/useFormValidation'
 *
 *   const { handleSubmit, errors, isSubmitting } = useForm({
 *     validationSchema: toTypedSchema(loginSchema),
 *   })
 */

import { z } from "zod";

// ── Helpers ──────────────────────────────────────────────

/** Phone number: 10 digits, starting with 0 */
const phoneRegex = /^0[1-9]\d{8}$/;

/** French postal code: 5 digits */
const postalCodeRegex = /^\d{5}$/;

const requiredMsg = "Ce champ est requis";
const tooShortMsg = (min: number) => `Minimum ${min} caractères`;
const tooLongMsg = (max: number) => `Maximum ${max} caractères`;

// ── Login ────────────────────────────────────────────────

export const loginSchema = z.object({
  username: z.string({ message: requiredMsg }).min(1, requiredMsg).min(3, tooShortMsg(3)),
  password: z.string({ message: requiredMsg }).min(1, requiredMsg).min(3, tooShortMsg(3)),
});

export type LoginForm = z.infer<typeof loginSchema>;

// ── Client ───────────────────────────────────────────────

export const clientSchema = z.object({
  full_name: z.string({ message: requiredMsg }).min(1, requiredMsg).min(2, tooShortMsg(2)).max(255, tooLongMsg(255)),
  phone: z
    .string({ message: requiredMsg })
    .min(1, requiredMsg)
    .regex(phoneRegex, "Numéro de téléphone invalide (ex: 0612345678)"),
  email: z.string().email("Email invalide").optional().or(z.literal("")),
  address: z.string({ message: requiredMsg }).min(1, requiredMsg).min(5, tooShortMsg(5)).max(500, tooLongMsg(500)),
  postal_code: z.string().regex(postalCodeRegex, "Code postal invalide (5 chiffres)").optional().or(z.literal("")),
  city: z.string().max(255, tooLongMsg(255)).optional().or(z.literal("")),
  notes: z.string().max(2000, tooLongMsg(2000)).optional().or(z.literal("")),
});

export type ClientForm = z.infer<typeof clientSchema>;

export const clientCreateSchema = clientSchema.required({
  full_name: true,
  phone: true,
  address: true,
});

export type ClientCreateForm = z.infer<typeof clientCreateSchema>;

// ── Intervention ──────────────────────────────────────────────────

export const interventionSchema = z.object({
  client_id: z
    .number({ message: requiredMsg, invalid_type_error: requiredMsg })
    .int()
    .positive("Veuillez sélectionner un client")
    .nullish(),
  title: z
    .string({ message: requiredMsg, invalid_type_error: requiredMsg })
    .min(1, requiredMsg)
    .min(3, tooShortMsg(3))
    .max(255, tooLongMsg(255)),
  description: z.string().max(2000, tooLongMsg(2000)).optional().or(z.literal("")),
  scheduled_date: z
    .union([z.string().min(1, requiredMsg), z.date()])
    .transform((v) => (v instanceof Date ? v.toISOString().split("T")[0] : v)),
  priority: z.enum(["basse", "normale", "haute", "urgente"]).optional().default("normale"),
});

export type InterventionForm = z.infer<typeof interventionSchema>;

// ── Material ─────────────────────────────────────────────

export const materialSchema = z.object({
  name: z.string({ message: requiredMsg }).min(1, requiredMsg).min(2, tooShortMsg(2)).max(255, tooLongMsg(255)),
  quantity: z.string({ message: requiredMsg }).min(1, requiredMsg).max(100, tooLongMsg(100)),
});

export type MaterialForm = z.infer<typeof materialSchema>;

// ── Profile update ───────────────────────────────────────

export const profileSchema = z.object({
  email: z.string().email("Email invalide").optional().or(z.literal("")),
  full_name: z.string().min(2, tooShortMsg(2)).max(255, tooLongMsg(255)).optional().or(z.literal("")),
});

export type ProfileForm = z.infer<typeof profileSchema>;
