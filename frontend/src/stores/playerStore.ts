import { create } from "zustand"
import type { ChapterFile } from "@/types"

interface PlayerStore {
  addonId: string | null
  itemId: string | null
  itemTitle: string | null
  files: ChapterFile[]
  currentIndex: number
  isPlaying: boolean
  position: number
  duration: number
  libraryItemId: string | null

  loadBook(
    addonId: string,
    itemId: string,
    title: string,
    files: ChapterFile[],
    libraryItemId: string | null,
    startIndex?: number
  ): void
  setCurrentIndex(i: number): void
  setPlaying(b: boolean): void
  setPosition(n: number): void
  setDuration(n: number): void
  nextTrack(): void
  prevTrack(): void
}

export const usePlayerStore = create<PlayerStore>((set, get) => ({
  addonId: null,
  itemId: null,
  itemTitle: null,
  files: [],
  currentIndex: 0,
  isPlaying: false,
  position: 0,
  duration: 0,
  libraryItemId: null,

  loadBook(addonId, itemId, title, files, libraryItemId, startIndex = 0) {
    set({
      addonId,
      itemId,
      itemTitle: title,
      files,
      currentIndex: startIndex,
      isPlaying: true,
      position: 0,
      duration: 0,
      libraryItemId,
    })
  },

  setCurrentIndex(i) {
    set({ currentIndex: i, position: 0, duration: 0 })
  },

  setPlaying(b) {
    set({ isPlaying: b })
  },

  setPosition(n) {
    set({ position: n })
  },

  setDuration(n) {
    set({ duration: n })
  },

  nextTrack() {
    const { currentIndex, files } = get()
    if (currentIndex < files.length - 1) {
      set({ currentIndex: currentIndex + 1, position: 0, duration: 0 })
    } else {
      set({ isPlaying: false })
    }
  },

  prevTrack() {
    const { currentIndex } = get()
    if (currentIndex > 0) {
      set({ currentIndex: currentIndex - 1, position: 0, duration: 0 })
    }
  },
}))
