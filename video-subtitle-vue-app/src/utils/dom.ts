// src/utils/dom.ts
export function getElement(selector: string): HTMLElement | null {
  return document.querySelector(selector);
}

export function createElement(tag: string, className?: string): HTMLElement {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  return element;
}

export function appendChild(parent: HTMLElement, child: HTMLElement): void {
  parent.appendChild(child);
}

export function removeChild(parent: HTMLElement, child: HTMLElement): void {
  parent.removeChild(child);
}

export function setAttribute(element: HTMLElement, name: string, value: string): void {
  element.setAttribute(name, value);
}

export function removeAttribute(element: HTMLElement, name: string): void {
  element.removeAttribute(name);
}

export function addEventListener(element: HTMLElement, event: string, handler: EventListener): void {
  element.addEventListener(event, handler);
}

export function removeEventListener(element: HTMLElement, event: string, handler: EventListener): void {
  element.removeEventListener(event, handler);
}