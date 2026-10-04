import { createClient } from '@supabase/supabase-js'
import { env } from './config/env'

const supabaseUrl = env.NEXT_PUBLIC_SUPABASE_URL || 'https://gjbijluacysjudkvpivd.supabase.co'
const supabaseAnonKey = env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
})
