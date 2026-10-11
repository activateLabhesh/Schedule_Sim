import { clamp } from './util.js';

export class Playback {
  constructor({ onRender, getInterval, onState }) {
    this.onRender = onRender;
    this.getInterval = getInterval;
    this.onState = onState;
    this.tick = 0;
    this.last = 0;
    this.timer = null;
  }

  get playing() {
    return this.timer !== null;
  }

  load(length) {
    this.stop();
    this.last = Math.max(0, length - 1);
    this.tick = 0;
    this.onRender(this.tick);
  }

  seek(value) {
    this.tick = clamp(value, 0, this.last);
    this.onRender(this.tick);
  }

  step(delta) {
    this.seek(this.tick + delta);
  }

  toggle() {
    this.playing ? this.stop() : this.start();
  }

  start() {
    if (this.playing) return;
    if (this.tick >= this.last) this.tick = 0;
    this.timer = setInterval(() => {
      if (this.tick >= this.last) {
        this.stop();
        return;
      }
      this.seek(this.tick + 1);
    }, this.getInterval());
    this.onState?.(true);
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.onState?.(false);
  }
}
