#version 330

in vec3 vertexPosition;

uniform mat4 matProjection;
uniform mat4 matView;

out vec3 fragPosition;

void main()
{
    // Direction to fetch from cubemap
    fragPosition = vertexPosition;

    // Remove the broadcast from the view matrix: the skybox is always around the camera
    mat4 rotView = mat4(mat3(matView));
    vec4 clipPos = matProjection * rotView * vec4(vertexPosition, 1.0);

    // z = w → depth 1.0, skybox is always behind everything
    gl_Position = clipPos.xyww;
}