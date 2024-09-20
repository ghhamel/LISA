/**
 Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

 Licensed under the Apache License, Version 2.0 (the "License").
 You may not use this file except in compliance with the License.
 You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 */
import { z } from 'zod';
import { AttributeEditorSchema } from '../form/environment-variables';

export enum ModelStatus {
    Creating = 'Creating',
    InService = 'InService',
    Stopping = 'Stopping',
    Stopped = 'Stopped',
    Updating = 'Updating',
    Deleting = 'Deleting',
    Failed = 'Failed',
}

export enum ModelType {
    textgen = 'textgen',
    embedding = 'embedding',
}

export enum InferenceContainer {
    TGI = 'tgi',
    TEI = 'tei',
    VLLM = 'vllm',
    INSTRUCTOR = 'instructor',
}

export type IContainerHealthCheckConfig = {
    command: string[];
    interval: number;
    startPeriod: number;
    timeout: number;
    retries: number;
};

export type IContainerConfigImage = {
    baseImage: string;
    path: string;
    type: string;
};

export type IMetricConfig = {
    albMetricName: string;
    targetValue: number;
    duration: number;
    estimatedInstanceWarmup: number;
};

export type ILoadBalancerHealthCheckConfig = {
    path: string;
    interval: number;
    timeout: number;
    healthyThresholdCount: number;
    unhealthyThresholdCount: number;
};

export type ILoadBalancerConfig = {
    healthCheckConfig: ILoadBalancerHealthCheckConfig
};

export type IAutoScalingConfig = {
    minCapacity: number;
    maxCapacity: number;
    cooldown: number;
    defaultInstanceWarmup: number;
    metricConfig: IMetricConfig;
};

export type IContainerConfig = {
    baseImage: IContainerConfigImage;
    sharedMemorySize: number;
    healthCheckConfig: IContainerHealthCheckConfig;
    environment?: Record<string, string>[];
};

export type IModel = {
    modelId: string;
    modelName: string;
    modelUrl: string;
    streaming: boolean;
    modelType: ModelType;
    instanceType: string;
    inferenceContainer: InferenceContainer;
    containerConfig: IContainerConfig;
    autoScalingConfig: IAutoScalingConfig;
    loadBalancerConfig: ILoadBalancerConfig;
};

export type IModelListResponse = {
    models: IModel[];
};

export type IModelRequest = {
    modelId: string;
    modelName: string;
    modelUrl: string;
    streaming: boolean;
    modelType: ModelType;
    instanceType: string;
    inferenceContainer: InferenceContainer;
    containerConfig: IContainerConfig;
    autoScalingConfig: IAutoScalingConfig;
    loadBalancerConfig: ILoadBalancerConfig;
    lisaHostedModel: boolean;
};

const containerHealthCheckConfigSchema = z.object({
    command: z.array(z.string()).default(['CMD-SHELL', 'exit 0']),
    interval: z.number().default(10),
    startPeriod: z.number().default(30),
    timeout: z.number().default(5),
    retries: z.number().default(2),
});


const containerConfigImageSchema = z.object({
    baseImage: z.string().default(''),
    path: z.string().default(''),
    type: z.string().default(''),
});

export const metricConfigSchema = z.object({
    albMetricName: z.string().default(''),
    targetValue: z.number().default(0),
    duration: z.number().default(60),
    estimatedInstanceWarmup: z.number().default(180),
});

export const loadBalancerHealthCheckConfigSchema = z.object({
    path: z.string().default(''),
    interval: z.number().default(10),
    timeout: z.number().default(5),
    healthyThresholdCount: z.number().default(1),
    unhealthyThresholdCount: z.number().default(1),
});

export const loadBalancerConfigSchema = z.object({
    healthCheckConfig: loadBalancerHealthCheckConfigSchema.default(loadBalancerHealthCheckConfigSchema.parse({})),
});

export const autoScalingConfigSchema = z.object({
    minCapacity: z.number().min(1).default(1),
    maxCapacity: z.number().min(1).default(2),
    cooldown: z.number().min(1).default(420),
    defaultInstanceWarmup: z.number().default(180),
    metricConfig: metricConfigSchema.default(metricConfigSchema.parse({})),
});

export const containerConfigSchema = z.object({
    baseImage: containerConfigImageSchema.default(containerConfigImageSchema.parse({})),
    sharedMemorySize: z.number().min(0).default(0),
    healthCheckConfig: containerHealthCheckConfigSchema.default(containerHealthCheckConfigSchema.parse({})),
    environment: AttributeEditorSchema,
});

export const ModelRequestSchema = z.object({
    modelId: z.string().min(1).default(' '),
    modelName: z.string().min(1).default(' '),
    modelUrl: z.string().default(''),
    streaming: z.boolean().default(false),
    lisaHostedModel: z.boolean().default(false),
    modelType: z.nativeEnum(ModelType).default(ModelType.textgen),
    instanceType: z.string().default(''),
    inferenceContainer: z.nativeEnum(InferenceContainer).optional(),
    containerConfig: containerConfigSchema.default(containerConfigSchema.parse({})),
    autoScalingConfig: autoScalingConfigSchema.default(autoScalingConfigSchema.parse({})),
    loadBalancerConfig: loadBalancerConfigSchema.default(loadBalancerConfigSchema.parse({})),
});