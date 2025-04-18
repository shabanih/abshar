     document.addEventListener('DOMContentLoaded', function () {
        const tagInput = document.getElementById('id_tag');
        const tagPreview = document.getElementById('tag-preview');

        // Function to update the tag preview
        function updateTagPreview() {
            const tags = tagInput.value.split(' ').map(tag => tag.trim()).filter(tag => tag !== "");

            // Clear the current content
            tagPreview.innerHTML = '';

            // Add each tag as a styled element
            tags.forEach(tag => {
                const tagElement = document.createElement('span');
                tagElement.textContent = tag;
                tagElement.style.display = 'inline-block';
                tagElement.style.margin = '5px';
                tagElement.style.padding = '5px 10px';
                tagElement.style.border = '1px solid #007bff';
                tagElement.style.borderRadius = '15px';
                tagElement.style.backgroundColor = '#e7f3ff';
                tagElement.style.color = '#007bff';

                tagPreview.appendChild(tagElement);
            });
        }

        // Add event listeners to update the preview on input change
        tagInput.addEventListener('input', updateTagPreview);

        // Initial preview update
        updateTagPreview();
    });