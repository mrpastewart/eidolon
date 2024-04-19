// This file is auto-generated by @hey-api/openapi-ts


export type HTTPValidationError = {
    detail?: Array<ValidationError>;
};

export type UsageDelta = {
    type?: 'delta';
    used_delta?: number;
    allowed_delta?: number;
    extra?: {
        [key: string]: unknown;
    };
};

export type UsageReset = {
    type?: 'reset';
    used?: number;
    allowed?: number;
    extra?: {
        [key: string]: unknown;
    };
};

export type UsageSummary = {
    subject: string;
    used: number;
    allowed: number;
};

export type ValidationError = {
    loc: Array<(string | number)>;
    msg: string;
    type: string;
};

export type $OpenApiTs = {
    '/health': {
        get: {
            res: {
                /**
 * Successful Response
 */
                200: unknown;
            };
        };
    };
    '/subjects/{subject_id}': {
        delete: {
            req: {
                subjectId: string;
            };
            res: {
                /**
 * Successful Response
 */
                200: {
                    [key: string]: unknown;
                };
            };
        };
        get: {
            req: {
                subjectId: string;
            };
            res: {
                /**
 * Successful Response
 */
                200: UsageSummary;
            };
        };
    };
    '/subjects/{subject_id}/transactions': {
        post: {
            req: {
                requestBody: UsageDelta | UsageReset;
                subjectId: string;
            };
            res: {
                /**
 * Successful Response
 */
                200: UsageSummary;
            };
        };
    };
};