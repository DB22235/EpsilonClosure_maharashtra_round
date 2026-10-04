'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from './supabase'

import { api } from './api'

interface AuthContextType {
  user: User | null
  session: Session | null
  token: string | null
  role: 'ADMIN' | 'USER' | null
  isAdmin: boolean
  loading: boolean
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>
  signUp: (email: string, password: string) => Promise<{ error: Error | null }>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  token: null,
  role: null,
  isAdmin: false,
  loading: true,
  signIn: async () => ({ error: null }),
  signUp: async () => ({ error: null }),
  signOut: async () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [role, setRole] = useState<'ADMIN' | 'USER' | null>(null)
  const [loading, setLoading] = useState(true)

  const isAdmin = role === 'ADMIN'

  const resolveRole = async (currentToken: string | null) => {
    if (!currentToken) {
      setRole(null)
      return
    }
    try {
      const meData = await api.me()
      const resolvedRole = meData?.profile?.role?.toUpperCase() === 'ADMIN' ? 'ADMIN' : 'USER'
      setRole(resolvedRole)
    } catch {
      setRole('USER')
    }
  }

  useEffect(() => {
    // 1. Get initial session
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      setToken(session?.access_token ?? null)
      if (session?.access_token) {
        await resolveRole(session.access_token)
      } else {
        setRole(null)
      }
      setLoading(false)
    })

    // 2. Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
      setToken(session?.access_token ?? null)
      if (session?.access_token) {
        await resolveRole(session.access_token)
      } else {
        setRole(null)
      }
      setLoading(false)
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  const signIn = async (email: string, password: string) => {
    let { data, error } = await supabase.auth.signInWithPassword({ email, password })

    // Auto-recover unconfirmed emails
    if (error && error.message?.toLowerCase().includes('not confirmed')) {
      try {
        await api.confirmEmail(email)
        const retry = await supabase.auth.signInWithPassword({ email, password })
        data = retry.data
        error = retry.error
      } catch (confirmErr) {
        console.warn('[Auth] Failed to auto-confirm email:', confirmErr)
      }
    }

    if (!error && data?.session) {
      setSession(data.session)
      setUser(data.session.user)
      setToken(data.session.access_token)
      await resolveRole(data.session.access_token)
      setLoading(false)
    }
    return { error }
  }

  const signUp = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signUp({ email, password })

    if (!error && (data?.user || data?.session)) {
      try {
        // Auto-confirm newly registered user immediately in database
        await api.confirmEmail(email)
      } catch (confirmErr) {
        console.warn('[Auth] Failed to auto-confirm newly created email:', confirmErr)
      }

      if (data?.session) {
        setSession(data.session)
        setUser(data.session.user)
        setToken(data.session.access_token)
        await resolveRole(data.session.access_token)
        setLoading(false)
      } else {
        // Automatically establish session if Supabase did not grant one due to email confirmation setting
        const loginRes = await supabase.auth.signInWithPassword({ email, password })
        if (loginRes.data?.session) {
          setSession(loginRes.data.session)
          setUser(loginRes.data.session.user)
          setToken(loginRes.data.session.access_token)
          await resolveRole(loginRes.data.session.access_token)
          setLoading(false)
        }
      }
    }

    return { error }
  }

  const signOut = async () => {
    await supabase.auth.signOut()
    setSession(null)
    setUser(null)
    setToken(null)
    setRole(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        token,
        role,
        isAdmin,
        loading,
        signIn,
        signUp,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
