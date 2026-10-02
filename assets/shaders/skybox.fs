#version 330

in vec3 fragPosition;

uniform samplerCube environmentMap;

out vec4 finalColor;

void main()
{
    vec3 color = texture(environmentMap, fragPosition).rgb;
    finalColor = vec4(color, 1.0);
}