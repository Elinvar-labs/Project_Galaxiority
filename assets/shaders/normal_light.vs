#version 330

in vec3 vertexPosition;
in vec3 vertexNormal;
in vec2 texCoord;

out vec3 fragNormal;
out vec2 fragTexCoord;
out vec3 fragPos; // <--- Передаём позицию фрагмента

uniform mat4 mvp;
uniform mat3 normalMatrix;
uniform mat4 modelMatrix;

void main() {
    gl_Position = mvp * vec4(vertexPosition, 1.0);

    // Мировая позиция фрагмента (нужна для света)
    fragPos = (modelMatrix * vec4(vertexPosition, 1.0)).xyz;

    fragNormal = normalize(normalMatrix * vertexNormal);
    fragTexCoord = texCoord;
}
