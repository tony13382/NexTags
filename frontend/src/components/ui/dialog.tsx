import * as React from "react"
import { cn } from "@/lib/utils"
import { X } from "lucide-react"

interface DialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    children: React.ReactNode
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
    if (!open) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50"
                onClick={() => onOpenChange(false)}
            />
            {/* Dialog content */}
            <div className="relative z-10 w-full max-w-lg mx-4">
                {children}
            </div>
        </div>
    )
}

type DialogContentProps = React.ComponentProps<"div">

export function DialogContent({ className, children, ...props }: DialogContentProps) {
    return (
        <div
            className={cn(
                "bg-white rounded-lg shadow-lg p-6 max-h-[90vh] overflow-y-auto",
                className
            )}
            {...props}
        >
            {children}
        </div>
    )
}

type DialogHeaderProps = React.ComponentProps<"div">

export function DialogHeader({ className, children, ...props }: DialogHeaderProps) {
    return (
        <div
            className={cn("flex items-center justify-between mb-4", className)}
            {...props}
        >
            {children}
        </div>
    )
}

type DialogTitleProps = React.ComponentProps<"h2">

export function DialogTitle({ className, children, ...props }: DialogTitleProps) {
    return (
        <h2
            className={cn("text-lg font-semibold text-gray-900", className)}
            {...props}
        >
            {children}
        </h2>
    )
}

type DialogDescriptionProps = React.ComponentProps<"p">

export function DialogDescription({ className, children, ...props }: DialogDescriptionProps) {
    return (
        <p
            className={cn("text-sm text-gray-600 mt-1", className)}
            {...props}
        >
            {children}
        </p>
    )
}

interface DialogCloseProps {
    onClose: () => void
}

export function DialogClose({ onClose }: DialogCloseProps) {
    return (
        <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
        >
            <X className="w-5 h-5" />
        </button>
    )
}

type DialogFooterProps = React.ComponentProps<"div">

export function DialogFooter({ className, children, ...props }: DialogFooterProps) {
    return (
        <div
            className={cn("flex justify-end space-x-2 mt-6", className)}
            {...props}
        >
            {children}
        </div>
    )
}