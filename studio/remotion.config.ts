// Studio/CLI defaults. tools/render.py renders through render.mjs, which sets the same options.
import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setConcurrency(2);
