// Animation-related type definitions
// These types can be used when implementing reactbits components

export interface BaseAnimationProps {
  /** Custom className for styling */
  className?: string
  /** Inline styles */
  style?: React.CSSProperties
  /** Animation duration in seconds */
  duration?: number
  /** Animation delay in seconds */
  delay?: number
  /** Whether animation should loop */
  loop?: boolean
}

export interface TextAnimationProps extends BaseAnimationProps {
  /** Text content to animate */
  text: string
  /** Animation speed/timing */
  speed?: number
}

export interface BackgroundAnimationProps extends BaseAnimationProps {
  /** Background color */
  color?: string
  /** Animation intensity */
  intensity?: number
}

export interface InteractiveAnimationProps extends BaseAnimationProps {
  /** Whether to respond to hover */
  onHover?: boolean
  /** Whether to respond to click */
  onClick?: boolean
}

// Common animation easing types
export type AnimationEasing =
  | 'linear'
  | 'ease'
  | 'ease-in'
  | 'ease-out'
  | 'ease-in-out'
  | 'elastic'
  | 'bounce'
  | string // Custom easing functions

// Animation direction types
export type AnimationDirection =
  | 'normal'
  | 'reverse'
  | 'alternate'
  | 'alternate-reverse'

// Motion preferences
export interface MotionPreferences {
  /** Respect user's reduced motion preference */
  respectMotionPreference?: boolean
  /** Fallback for reduced motion */
  reducedMotionFallback?: React.ReactNode
}