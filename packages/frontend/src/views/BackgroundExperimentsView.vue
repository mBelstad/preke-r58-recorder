<script setup lang="ts">
/**
 * Background Experiments View
 * Creative explorations using the geometric pattern background
 * Navigate to /experiments to view these live
 */
import { ref } from 'vue'
import geometricPattern from '@/assets/geometric-pattern.jpeg'

const activeExperiment = ref<number>(1)
const experiments = [
  { id: 1, name: 'Dark Parallax', desc: 'Subtle dark overlay with parallax movement' },
  { id: 2, name: 'Gold Tint', desc: 'Dark version with gold/amber accent glow' },
  { id: 3, name: 'Animated Reveal', desc: 'Pattern reveals with animated mask' },
  { id: 4, name: 'Glassmorphism Hero', desc: 'Glass card floating over moving pattern' },
  { id: 5, name: 'Split Diagonal', desc: 'Diagonal split with pattern on one side' },
]
</script>

<template>
  <div class="experiments">
    <!-- Navigation -->
    <div class="experiments__nav">
      <h1 class="experiments__title">Background Experiments</h1>
      <div class="experiments__tabs">
        <button 
          v-for="exp in experiments" 
          :key="exp.id"
          @click="activeExperiment = exp.id"
          class="experiments__tab"
          :class="{ 'experiments__tab--active': activeExperiment === exp.id }"
        >
          {{ exp.name }}
        </button>
      </div>
    </div>

    <!-- Experiment 1: Dark Parallax -->
    <div v-show="activeExperiment === 1" class="exp exp--parallax">
      <div class="exp__pattern-layer exp__pattern-layer--back">
        <img :src="geometricPattern" alt="" class="exp__pattern-img" />
        <div class="exp__dark-overlay"></div>
      </div>
      <div class="exp__pattern-layer exp__pattern-layer--front">
        <img :src="geometricPattern" alt="" class="exp__pattern-img exp__pattern-img--blur" />
        <div class="exp__dark-overlay exp__dark-overlay--heavy"></div>
      </div>
      <div class="exp__content">
        <h2 class="exp__heading">Dark Parallax</h2>
        <p class="exp__desc">The geometric pattern creates depth through layers moving at different speeds. Inverted and darkened for dark mode.</p>
      </div>
    </div>

    <!-- Experiment 2: Gold Tint -->
    <div v-show="activeExperiment === 2" class="exp exp--gold">
      <div class="exp__pattern-layer">
        <img :src="geometricPattern" alt="" class="exp__pattern-img" />
        <div class="exp__gold-overlay"></div>
        <div class="exp__gold-glow exp__gold-glow--1"></div>
        <div class="exp__gold-glow exp__gold-glow--2"></div>
      </div>
      <div class="exp__content">
        <h2 class="exp__heading" style="color: var(--preke-gold);">Gold Accent</h2>
        <p class="exp__desc">Subtle gold/amber glow over the darkened pattern. The Preke brand color adds warmth to the geometric shapes.</p>
      </div>
    </div>

    <!-- Experiment 3: Animated Reveal -->
    <div v-show="activeExperiment === 3" class="exp exp--reveal">
      <div class="exp__pattern-layer">
        <img :src="geometricPattern" alt="" class="exp__pattern-img" />
        <div class="exp__dark-overlay"></div>
        <div class="exp__reveal-mask"></div>
      </div>
      <div class="exp__content">
        <h2 class="exp__heading">Animated Reveal</h2>
        <p class="exp__desc">Pattern gradually reveals with an animated diagonal wipe. Perfect for loading screens or transitions.</p>
      </div>
    </div>

    <!-- Experiment 4: Glassmorphism Hero -->
    <div v-show="activeExperiment === 4" class="exp exp--glass">
      <div class="exp__pattern-layer exp__pattern-layer--moving">
        <img :src="geometricPattern" alt="" class="exp__pattern-img" />
        <div class="exp__dark-overlay exp__dark-overlay--gradient"></div>
      </div>
      <div class="exp__glass-card">
        <h2 class="exp__heading">Glassmorphism</h2>
        <p class="exp__desc">Frosted glass card floating over slowly moving pattern. Combines with blur for depth effect.</p>
        <button class="exp__glass-btn">Get Started</button>
      </div>
    </div>

    <!-- Experiment 5: Split Diagonal -->
    <div v-show="activeExperiment === 5" class="exp exp--split">
      <div class="exp__split-pattern">
        <img :src="geometricPattern" alt="" class="exp__pattern-img" />
        <div class="exp__dark-overlay exp__dark-overlay--purple"></div>
      </div>
      <div class="exp__split-solid"></div>
      <div class="exp__content exp__content--left">
        <h2 class="exp__heading">Split Design</h2>
        <p class="exp__desc">Diagonal split creates visual interest. Pattern on one side, solid on the other.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.experiments {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--preke-bg);
}

.experiments__nav {
  position: relative;
  z-index: 100;
  padding: 1.5rem 2rem;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--preke-border);
}

.experiments__title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--preke-text);
  margin-bottom: 1rem;
}

.experiments__tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.experiments__tab {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--preke-text-muted);
  background: transparent;
  border: 1px solid var(--preke-border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.experiments__tab:hover {
  color: var(--preke-text);
  border-color: var(--preke-border-light);
}

.experiments__tab--active {
  color: var(--preke-gold);
  background: rgba(224, 160, 48, 0.1);
  border-color: var(--preke-gold);
}

/* Base experiment styles */
.exp {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.exp__pattern-layer {
  position: absolute;
  inset: 0;
}

.exp__pattern-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: invert(1) brightness(0.15) contrast(1.2);
}

.exp__pattern-img--blur {
  filter: invert(1) brightness(0.1) contrast(1.2) blur(8px);
}

.exp__dark-overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 15, 20, 0.7);
}

.exp__dark-overlay--heavy {
  background: rgba(15, 15, 20, 0.85);
}

.exp__dark-overlay--gradient {
  background: linear-gradient(135deg, rgba(15, 15, 20, 0.9) 0%, rgba(15, 15, 20, 0.6) 100%);
}

.exp__dark-overlay--purple {
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.3) 0%, rgba(15, 15, 20, 0.8) 100%);
}

.exp__content {
  position: relative;
  z-index: 10;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
}

.exp__content--left {
  align-items: flex-start;
  text-align: left;
  max-width: 50%;
  padding-left: 4rem;
}

.exp__heading {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--preke-text);
  margin-bottom: 1rem;
}

.exp__desc {
  font-size: 1rem;
  color: var(--preke-text-muted);
  max-width: 500px;
  line-height: 1.6;
}

/* Experiment 1: Parallax */
.exp--parallax .exp__pattern-layer--back {
  transform: scale(1.1);
  animation: parallax-back 20s ease-in-out infinite;
}

.exp--parallax .exp__pattern-layer--front {
  animation: parallax-front 15s ease-in-out infinite;
}

@keyframes parallax-back {
  0%, 100% { transform: scale(1.1) translate(0, 0); }
  50% { transform: scale(1.1) translate(-20px, -10px); }
}

@keyframes parallax-front {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(10px, 5px); }
}

/* Experiment 2: Gold */
.exp__gold-overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 15, 20, 0.85);
  mix-blend-mode: multiply;
}

.exp__gold-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
}

.exp__gold-glow--1 {
  width: 500px;
  height: 500px;
  top: -20%;
  right: -10%;
  background: radial-gradient(circle, rgba(224, 160, 48, 0.25) 0%, transparent 70%);
  animation: gold-glow-1 8s ease-in-out infinite;
}

.exp__gold-glow--2 {
  width: 400px;
  height: 400px;
  bottom: -15%;
  left: -5%;
  background: radial-gradient(circle, rgba(217, 152, 30, 0.2) 0%, transparent 70%);
  animation: gold-glow-2 10s ease-in-out infinite;
}

@keyframes gold-glow-1 {
  0%, 100% { transform: translate(0, 0); opacity: 0.8; }
  50% { transform: translate(-30px, 20px); opacity: 1; }
}

@keyframes gold-glow-2 {
  0%, 100% { transform: translate(0, 0); opacity: 0.6; }
  50% { transform: translate(20px, -30px); opacity: 0.9; }
}

/* Experiment 3: Reveal */
.exp__reveal-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 0%, transparent 50%, var(--preke-bg) 50%, var(--preke-bg) 100%);
  animation: reveal-wipe 4s ease-in-out infinite;
}

@keyframes reveal-wipe {
  0%, 10% { 
    clip-path: polygon(0 0, 0 0, 0 100%, 0 100%); 
  }
  50%, 60% { 
    clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); 
  }
  100% { 
    clip-path: polygon(100% 0, 100% 0, 100% 100%, 100% 100%); 
  }
}

/* Experiment 4: Glass */
.exp__pattern-layer--moving .exp__pattern-img {
  animation: slow-drift 30s linear infinite;
}

@keyframes slow-drift {
  0% { transform: scale(1.2) translate(0, 0); }
  50% { transform: scale(1.2) translate(-3%, -2%); }
  100% { transform: scale(1.2) translate(0, 0); }
}

.exp__glass-card {
  position: relative;
  z-index: 10;
  padding: 3rem 4rem;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  text-align: center;
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.exp__glass-btn {
  margin-top: 1.5rem;
  padding: 0.875rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--preke-bg);
  background: var(--preke-gold);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.exp__glass-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(224, 160, 48, 0.3);
}

/* Experiment 5: Split */
.exp__split-pattern {
  position: absolute;
  top: 0;
  right: 0;
  width: 60%;
  height: 100%;
  clip-path: polygon(30% 0, 100% 0, 100% 100%, 0 100%);
}

.exp__split-solid {
  position: absolute;
  top: 0;
  left: 0;
  width: 50%;
  height: 100%;
  background: var(--preke-bg);
}
</style>

