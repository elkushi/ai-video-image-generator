// One composition per aspect ratio, all driven by the same props.json (tools/build_props.py).
import React from 'react';
import {Composition, type CalculateMetadataFunction} from 'remotion';
import sample from './sample-props.json';
import type {VideoProps} from './types';
import {Video} from './Video';

const FORMATS = [
	{id: 'Video-9x16', width: 1080, height: 1920},
	{id: 'Video-1x1', width: 1080, height: 1080},
	{id: 'Video-4x5', width: 1080, height: 1350},
	{id: 'Video-16x9', width: 1920, height: 1080},
];

const calculateMetadata: CalculateMetadataFunction<VideoProps> = ({props}) => ({
	durationInFrames: Math.max(30, props.totalFrames),
});

export const Root: React.FC = () => (
	<>
		{FORMATS.map((f) => (
			<Composition
				key={f.id}
				id={f.id}
				component={Video}
				width={f.width}
				height={f.height}
				fps={30}
				durationInFrames={300}
				defaultProps={sample as unknown as VideoProps}
				calculateMetadata={calculateMetadata}
			/>
		))}
	</>
);
