"use server"

import { NextRequest, NextResponse } from "next/server"
import { db } from "@/db/db"
import { sessionsTable } from "@/db/schema"
import { eq } from "drizzle-orm"

export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const id = params.id

    if (!id) {
      return NextResponse.json(
        { isSuccess: false, message: "Session ID is required", data: null },
        { status: 400 }
      )
    }

    // End the session by setting isActive to false
    const [updatedSession] = await db
      .update(sessionsTable)
      .set({ isActive: false })
      .where(eq(sessionsTable.id, id))
      .returning()

    if (!updatedSession) {
      return NextResponse.json(
        { isSuccess: false, message: "Session not found", data: null },
        { status: 404 }
      )
    }

    return NextResponse.json({
      isSuccess: true,
      message: "Session ended successfully",
      data: updatedSession
    })
  } catch (error) {
    console.error("Error ending session:", error)
    return NextResponse.json(
      { isSuccess: false, message: "Failed to end session", data: null },
      { status: 500 }
    )
  }
} 